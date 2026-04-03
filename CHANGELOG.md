# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
準拠バージョン: 0.1.0

なお、本履歴は提供されたコードベースの内容から推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

- 今後のリリース用のプレースホルダ。

---

## [0.1.0] - 2026-04-03

初回リリース（推測）。日本株自動売買システム「KabuSys」のコア機能を実装。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を定義。
  - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution 等を想定（__all__ に data/strategy/execution/monitoring を公開）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動読み込み無効化オプション。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - Settings クラスでアプリ設定を公開（J-Quants、kabu API、LINE、DB パス、監視閾値、環境 / ログレベル検証など）。
  - 必須環境変数未設定時は明示的な ValueError を送出する _require() 実装。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult dataclass を実装し、取得・保存件数、品質問題、エラー情報を収集。
    - 差分取得、バックフィル、品質チェック設計に対応するユーティリティを実装（J-Quants クライアント呼び出しを想定）。
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブルの参照/更新、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、夜間更新ジョブ calendar_update_job）。
    - DB にデータが無い場合の曜日ベースフォールバック、最大探索日数制限、バックフィル・健全性チェックを実装。

  - ETL に関する補助モジュール公開（kabusys.data.etl = ETLResult の再エクスポート）。

- 研究 / ファクター（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、出来高関連）、Value（PER、ROE）ファクター計算を実装。
    - DuckDB を用いた SQL 集約＋Python での出力（(date, code) ベースの dict リスト）。
    - データ不足時の None 処理、ログ出力、スキャン範囲バッファ等を実装。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部依存を持たない純標準ライブラリ実装、境界チェック（horizons の検証）や ties の平均ランク処理を含む。

- AI / ニュース NLP（kabusys.ai）
  - news_nlp
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）に対してバッチでセンチメントを取得して ai_scores テーブルへ保存する機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window。
    - チャンク送信（最大 20 銘柄／呼び出し）、1 銘柄あたり記事数・文字数制限、JSON Mode を想定したレスポンス検証（厳格な JSON 抽出と検証）。
    - リトライ（429、ネットワーク、タイムアウト、5xx）を指数バックオフで実施。フェイルセーフ設計（API 失敗時は該当チャンクをスキップして継続）。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
  - regime_detector
    - 市場レジーム判定（market_regime テーブルへの書き込み）を実装。ETF 1321（日経225連動）の200日 MA 乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して daily レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタ、最大件数制限、OpenAI 呼び出し（gpt-4o-mini）に対するリトライ/フェイルセーフ、DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API キー注入可能、失敗時の macro_sentiment=0.0 フォールバック。

### Changed
- 設計上の方針と注意点（ドキュメント化）
  - 多くのモジュールで「datetime.today()/date.today() を内部参照しない」方針を徹底（ルックアヘッドバイアス防止）。date は呼び出し元から渡す設計。
  - DuckDB のバージョン互換性を考慮した実装（executemany の空リスト回避、リスト型バインドの回避等）。
  - OpenAI 呼び出しはモジュール間でプライベート関数を共有せず、それぞれ独立実装している（疎結合化）。

### Fixed
- エラー処理とロギングの強化
  - 各種 API 呼び出しや DB 書き込みの失敗時に適切にログを出す設計（warning/exception）。
  - DB 書き込み失敗時に ROLLBACK を試み、ROLLBACK 自体の失敗も警告ログで通知。
  - .env ファイル読み込み失敗時に警告を出すように変更。

### Security
- 環境変数の保護
  - 自動ロード時に既存の OS 環境変数を保護する仕組み（protected set を使用して .env から上書きされないように処理）。
  - 必須の機密情報（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）は明示的にチェックし未設定時に例外を投げる。

### Notes / Known limitations
- 一部指標は未実装（例: PBR・配当利回りは value ファクターで未実装）。
- news_nlp / regime_detector は外部 OpenAI API を利用するため、実稼働時は API キーと利用制限（コスト・レート制限）に注意が必要。
- calendar_update_job、ETL 処理等は jquants_client（外部モジュール）に依存しており、実行には該当クライアントの実装と認証情報が必要。
- テスト戦略として各種外部呼び出し（OpenAI 呼び出し等）はモック差し替えを想定している。

---

もし追加で実際のコミットメッセージや日付を与えていただければ、より正確で詳細な CHANGELOG を生成できます。