# Changelog

すべての重要な変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

※以下は現在のコードベースから推測して作成した初期リリースの変更履歴です。

## [Unreleased]
- 開発中の変更や次回リリース予定のノートをここに記載します。

## [0.1.0] - 2026-03-27
初回リリース。

### Added
- パッケージ全体
  - kabusys パッケージを公開（__version__ = 0.1.0）。
  - パッケージトップは data / strategy / execution / monitoring を公開する設計。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索（CWD 非依存）。
  - .env のパース機能強化:
    - export KEY=val 形式対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメントの扱いを適切に処理。
  - .env と .env.local の読み込み優先度を実装（OS 環境変数は保護）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定等の取得を型付きプロパティで行う。
  - 環境変数の必須チェックおよび妥当性検査（KABUSYS_ENV / LOG_LEVEL の許容値検証）。

- データ取得・ETL (kabusys.data.pipeline / etl)
  - ETLResult データクラスを追加し ETL の取得数、保存数、品質問題、エラー情報を集約。
  - 差分取得・バックフィル・品質チェックを念頭に置いた ETL パイプラインの骨子を実装（J-Quants クライアントと連携想定）。
  - DB 存在確認や最大日付取得等のユーティリティを提供。

- マーケットカレンダー管理 (kabusys.data.calendar_management)
  - market_calendar を用いた営業日判定ロジックを実装:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
  - データがない場合の曜日ベースのフォールバックを実装（DB とフォールバックの優先度を明確化）。
  - 夜間バッチ calendar_update_job を実装（J-Quants API からの差分取得、バックフィル、健全性チェック含む）。
  - DuckDB との互換性を考慮した日付・NULL ハンドリングを実装。

- 研究（Research）モジュール (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）などのファクター計算関数を実装。
    - DuckDB 上で SQL とウィンドウ関数を用いて高速に計算する設計。
    - データ不足時の None ハンドリングやログ出力。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、rank、factor_summary といった評価用ユーティリティを実装。
    - Spearman（ランク）相関の実装や同順位処理（平均ランク）を組み込み。

- AI を使ったニュース解析・レジーム判定 (kabusys.ai)
  - news_nlp:
    - raw_news + news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（ai_score）を生成。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算（calc_news_window）を実装。
    - 1銘柄あたりの記事数・文字数上限、バッチ処理（最大 20 銘柄/呼び出し）を実装。
    - API 呼び出しのリトライ（429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフ）とレスポンスバリデーションを実装。
    - レスポンスは JSON mode を期待し、堅牢なパースと検証を実装（未知コード無視、スコアのクリッピング）。
    - ai_scores テーブルへの冪等的な置換（DELETE→INSERT）ロジックを実装し、部分失敗時に既存スコアを保護。
  - regime_detector:
    - ETF 1321（日経225 連動型）を用いた 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（gpt-4o-mini）でのセンチメント取得、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API エラー時は安全策として macro_sentiment=0.0 にフォールバック。
    - モジュール間でプライベート関数を共有しない方針（test 用に _call_openai_api を patch 可能）。

- DuckDB を想定した DB 操作
  - 多くのモジュールで DuckDBPyConnection を利用するインターフェースを採用。
  - executemany の空リスト問題や日付型の取り扱い等、DuckDB 固有の注意点に配慮した実装。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- 環境変数の取り扱いに注意: 一部必須キーは Settings で取得時に ValueError を送出する（API キー未設定時など）。.env の読み込みは保護キーを考慮して OS 環境変数を上書きしない既定動作。

### Notes / Design decisions
- ルックアヘッドバイアス回避: 多くの分析・スコアリング関数は内部で datetime.today() / date.today() を参照せず、必ず外部から与えられる target_date を基準に処理する実装方針を採用。
- フェイルセーフ: 外部 API（OpenAI, J-Quants 等）失敗時でもプロセスを停止させず、安全値（例: 0.0）で継続する設計。DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で冪等性を担保。
- テスト容易性: OpenAI 呼び出し箇所は内部関数を patch して差し替え可能にしている（unittest.mock.patch を想定）。
- 互換性: DuckDB バージョン差分（executemany の制約や配列バインディングの違い）に配慮した実装。

---

今後のリリースで想定される追加項目（参考）
- strategy / execution / monitoring の実装詳細（注文実行ロジック、バックテスト、モニタリング、Slack 通知等）
- テストと CI 実装、ドキュメント追加（Usage Examples, API ドキュメント）
- パフォーマンスチューニングや大規模データ対応（並列化、キャッシュ等）
- セキュリティ強化（機密情報のより厳格な保護、シークレット管理統合）

もし特定のモジュール単位やより詳細な変更履歴（コミット単位やチケット番号等）が必要であれば、対象箇所を指定していただければさらに詳細な CHANGELOG を生成します。