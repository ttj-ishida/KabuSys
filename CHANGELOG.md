# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現行バージョン: 0.1.0

## [Unreleased]
（なし）

---

## [0.1.0] - 2026-03-28
初回リリース

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - パッケージ公開インターフェースを __all__ で整理（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を自動読み込み。
  - 自動読み込みの探索はパッケージのファイル位置を起点に .git / pyproject.toml を探してプロジェクトルートを特定（CWD に依存しない実装）。
  - .env 読み込み時の堅牢なパーサを実装：
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理等。
    - override / protected オプションにより既存 OS 環境変数の保護が可能。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、主要な環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）、LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev のヘルパー

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメント（score_news）
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - 一次ウィンドウ定義（JST基準）：前日 15:00 ～ 当日 08:30（UTC に変換して DB クエリ）。
    - チャンク送信（最大 20 銘柄 / コール）、1銘柄あたり最大記事数・文字数制限（トリム）を実装しトークン肥大化を防止。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ。
    - レスポンスの厳密バリデーション（JSON パース、"results" リスト、code/score 検証、数値チェック）と ±1.0 クリップ。
    - パーシャル成功に対応する書き込み戦略: 取得できた code のみ DELETE → INSERT（冪等保存、部分失敗時に既存データを保護）。
    - テスト容易性のため _call_openai_api を patch できる設計。
  - 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来マクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロセンチメントはニュースタイトル群を LLM（gpt-4o-mini）に渡して JSON 出力で取得。記事なしや API 失敗時は macro_sentiment = 0.0 をフォールバック。
    - レジームスコア計算、閾値判定、結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API 呼び出しの失敗耐性（再試行・5xx 判定・例外ハンドリング）を実装。
    - テスト時の差し替えポイント（_call_openai_api）を用意。

- データ基盤（kabusys.data）
  - ETL / パイプライン（pipeline）
    - ETLResult データクラスを公開（target_date、取得/保存件数、品質問題・エラー一覧などを保持）。
    - 差分更新、バックフィル、品質チェック（quality モジュール利用）を想定した ETL 設計（実装の骨子）。
    - DuckDB 上の最終日取得ユーティリティ等を提供。
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルを参照/更新するユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存（バックフィルと先読み、有効性チェックを含む）。
    - DB データがない場合は曜日ベースのフォールバック（土日非営業日扱い）。DB とフォールバックの一貫性を保つ設計。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）により無限ループ回避。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高変化率）、バリュー（PER、ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 処理、営業日ベースのホライゾン取り扱い等の実装。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）: LEAD を用いた任意ホライズンの取得（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算（calc_ic）: スピアマン（ランク）相関の実装、最低レコード数チェック。
    - ランク化ユーティリティ（rank）: 同順位は平均ランク、丸め処理で ties を扱う。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median の算出。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- （特記事項なし）

### Design / Implementation notes（設計上の重要点）
- ルックアヘッドバイアス対策:
  - score_news / score_regime / 各種リサーチ関数は内部で datetime.today() や date.today() を参照しない。必ず外部から target_date を与えることで将来情報の参照を防止。
  - DB クエリは target_date を明示的に排他条件（date < target_date など）で扱う設計が随所にある。
- データベース書き込みは冪等性を重視（DELETE → INSERT、トランザクション制御）。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスの堅牢な復元処理（余分な前後テキストから最外の {} を抽出する等）を実装。
- テスト容易性のため、外部 API 呼び出し箇所（_call_openai_api 等）を patch できる設計。
- DuckDB の executemany に関する互換性考慮（空リストバインド回避）を考慮した実装。

### Known issues / Roadmap
- news_nlp / regime_detector の OpenAI モデルや呼び出しパラメータは将来的に設定化（モデル名やタイムアウト等）する予定。
- strategy / execution / monitoring モジュールは本リリースではパブリックインターフェースを定義済みだが、実運用向けの実装・テスト・ドキュメント整備が今後の課題。
- 品質チェック（quality モジュール）については ETL に統合する運用フローを強化予定。

---

（注）この CHANGELOG はリポジトリ内のコード構造・ドキュメント文字列から推測して作成しています。実際のリリースノートとして公開する場合は、ビルド/パッケージ管理情報や実際の変更差分と照合の上で調整してください。