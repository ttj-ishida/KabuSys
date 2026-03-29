# Changelog

すべての変更は「Keep a Changelog」仕様に準拠します。  
このプロジェクトの初期リリース履歴を以下に記載します。

## [0.1.0] - 2026-03-29

### 追加
- パッケージ基本情報
  - パッケージ初期バージョンを `0.1.0` としてリリース。
  - パッケージトップに __all__ で公開モジュール群を定義（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装：
    - プロジェクトルートを .git または pyproject.toml を基準に探索して自動的に .env/.env.local をロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動ロードを無効化可能（テスト用途）。
    - .env.local は .env の上書き（override=True）として扱い、OS 環境変数は保護（protected）される。
  - .env パーサを独自実装：
    - export KEY=val, シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント処理に対応。
    - 無効行や不正な行を適切に無視。
  - Settings クラスを提供し、環境変数の取得やバリデーションをプロパティ経由で実施：
    - J-Quants / kabuステーション / Slack / DB パスなどの設定をプロパティ化。
    - KABUSYS_ENV / LOG_LEVEL 等の許容値チェックを実装。
    - デフォルトの DB パス（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）を設定。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp モジュール（score_news）:
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄別センチメントを算出。
    - バッチ処理（最大 20 銘柄/チャンク）・記事数/文字数のトリム・429/ネットワーク/5xx に対する指数的バックオフリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON 復元、キー/型チェック、未知コードの無視、スコアの ±1.0 クリップ）。
    - DuckDB への冪等的書き込み（DELETE → INSERT、部分失敗時に既存スコアを保護）。
    - テスト容易性のため OpenAI 呼出し（_call_openai_api）をモック差し替え可能。
    - 収集時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に計算するユーティリティ calc_news_window を提供。
  - regime_detector モジュール（score_regime）:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定。
    - OpenAI API 呼出しは独立実装で、失敗時は macro_sentiment=0.0 のフォールバックを行うフェイルセーフ設計。
    - DuckDB からのデータ取得はルックアヘッドバイアスを防ぐため target_date 未満（排他）で実施。
    - 冪等的な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - API リトライ・エラー処理、JSON パースの安全な取り扱いを実装。

- データプラットフォーム関連（kabusys.data）
  - calendar_management モジュール:
    - JPX カレンダー（market_calendar）管理、営業日判定と探索ユーティリティを提供：
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等。
    - DB にカレンダー登録がない場合は曜日（平日）に基づくフォールバックを採用。
    - 最大探索日数を定義して無限ループを防止（_MAX_SEARCH_DAYS）。
    - calendar_update_job により J-Quants API から差分取得して冪等保存（バックフィル・健全性チェックを実装）。
  - ETL パイプライン（pipeline）:
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分更新・バックフィル・品質チェック（quality）を念頭に置いた ETL 処理設計。
    - DuckDB のテーブル存在チェックや最大日付取得等のユーティリティ実装。
    - ETL の実行結果を辞書化する to_dict（品質問題は (check_name, severity, message) のタプル化）を提供。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュール:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比）を DuckDB 上で計算する関数群を実装（calc_momentum, calc_value, calc_volatility）。
    - データ不足時は None を返す設計。
    - DuckDB のウィンドウ関数や LAG/AVG を活用した実装。
    - PBR・配当利回りは現バージョンで未実装（注記）。
  - feature_exploration モジュール:
    - 将来リターン計算（calc_forward_returns、可変ホライズン対応、入力バリデーション）、IC（Spearman ランク相関）計算（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を持たず標準ライブラリ＋DuckDB で完結する設計。
    - ties の扱い（同順位は平均ランク）や数値の丸めで安定したランク付けを行う。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 既知の制限 / 注意事項
- OpenAI API の利用には環境変数 OPENAI_API_KEY または関数引数でのキー注入が必要。未設定時は ValueError を送出する（score_news, score_regime）。
- news_nlp/regime_detector は外部 API（OpenAI）に依存するため、ネットワーク問題やレート制限により一部処理がスキップされる可能性がある（フェイルセーフで空スコアあるいは 0.0 を返す実装）。
- 一部計算はデータ不足時に None を返す（例: MA200 欠如、ATR 窓が満たない等）。
- PBR / 配当利回り等の指標は現バージョンで未実装（将来的な拡張候補）。
- DuckDB の executemany は空リストを受け付けない挙動に配慮した実装になっている（互換性確保）。
- .env の自動ロードはプロジェクトルートを探索するため、パッケージ配布後は KABUSYS_DISABLE_AUTO_ENV_LOAD の設定を推奨するケースがある。

### 実装上の設計方針（ハイライト）
- ルックアヘッドバイアス回避のため、datetime.today() / date.today() を計算ロジック内部で参照しない設計（target_date を明示的に渡す方式）。
- API 呼び出しは冪等性・フェイルセーフを重視（部分失敗の保護、ログ出力、リトライ/バックオフ）。
- DuckDB を一次データストアとして SQL と Python を組み合わせた処理を行う。
- 単体テスト容易性のため、外部依存（OpenAI 呼出し等）を差し替え可能にしている（関数単位でモック可能）。

---

今後のリリースでは、以下を予定（例）:
- PBR / 配当利回り等バリュー指標の実装
- strategy / execution / monitoring モジュールの具体的実装・発展
- より詳細な品質チェック・ETL の自動化オプションの強化
- ドキュメント追加（API 使用例、運用手順、環境設定ガイド）

ご要望があれば、CHANGELOG の粒度（コミット単位・機能単位）や英語版の併記等も対応します。