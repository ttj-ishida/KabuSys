# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このファイルはコードベース（src/kabusys 以下）から推測して作成した初期の変更履歴です。

全般的な注記
- 本リリースはパッケージの初期公開相当（0.1.0）として想定しています。
- 日付は本ファイル生成日時（2026-03-29）を使用しています。
- 実装上の設計方針や既知の制約（DuckDB のバージョン依存、OpenAI の API キー必須など）を目立つ形で明記しています。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買システム「KabuSys」のコア機能を提供します。以下の主要サブシステムを実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開モジュール指定）。
- 環境設定 / ローダー（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パース機能を実装（export プレフィックス、シングル/ダブルクォート、コメントルール、エスケープ処理対応）。
  - OS 環境変数を保護するための protected セットや override 挙動を実装。
  - Settings クラスを提供し、J-Quants・kabu API・Slack・データベースパス・環境モード・ログレベル等の設定プロパティを公開。
  - 必須環境変数未設定時は _require() が ValueError を投げる。

- AI ニュース処理（kabusys.ai.news_nlp）
  - ニュースのタイムウィンドウ計算（JST ベースを UTC naive datetime に変換）。
  - raw_news と news_symbols から銘柄ごとに記事を集約、記事トリム（最大件数・最大文字数）。
  - OpenAI（gpt-4o-mini）を用いたバッチセンチメント解析（最大20銘柄 / チャンク）。
  - JSON モードでのレスポンス処理と厳格なバリデーション（results 配列、code/score 検証）。
  - スコア値を ±1.0 にクリップし、ai_scores テーブルへ置換（DELETE → INSERT）するトランザクション処理。
  - エラー／レート制限／ネットワーク断／5xx に対する指数バックオフリトライ。
  - テストしやすさのため _call_openai_api を patch 可能に実装。
  - フェイルセーフ: API 失敗時は該当チャンクをスキップし、他銘柄の既存スコアを保護する設計。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei 連動）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（bull / neutral / bear）。
  - prices_daily / raw_news / market_regime を参照し、冪等的に market_regime に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
  - OpenAI 呼び出しに対するリトライ・エラーハンドリング（RateLimit, APIConnectionError, APITimeout, APIError の扱い）を実装。API 失敗時は macro_sentiment=0.0 をフォールバック。
  - ルックアヘッドバイアス対策：target_date 未満のみを用いるクエリ、datetime.today() を参照しない設計。
  - OpenAI の API キーは引数で注入可能（api_key）かつ環境変数 OPENAI_API_KEY を使用。

- リサーチ（kabusys.research）
  - factor_research: モメンタム、ボラティリティ（ATR）、バリュー（PER, ROE）等の定量ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、Information Coefficient（calc_ic）、ファクター統計サマリー（factor_summary）、ランク変換（rank）を実装。
  - データ集約は DuckDB + SQL ウィンドウ関数で行い、外部ライブラリ（pandas 等）に依存しない実装。

- データプラットフォーム（kabusys.data）
  - calendar_management: market_calendar の読み書き・JPX カレンダー差分更新ジョブ（calendar_update_job）、営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。DB の値優先・未登録日は曜日ベースでフォールバックする一貫した挙動。
  - pipeline / etl: ETLResult データクラス、ETL パイプライン設計（差分取得、保存、品質チェック）のインターフェース。backfill、calendar lookahead、品質問題の集約ロジックを用意。
  - jquants_client との統合ポイント（fetch/save 系）を想定。

- その他
  - DuckDB を前提としたクエリや DuckDB の executemany の空リスト制約への対応（空リスト時は実行しない）などの実運用上の配慮を多数実装。
  - ロギングを各モジュールに配置し、情報／警告／例外の記録を行う。

### Changed
（初回リリースのため該当なし）

### Fixed
（初回リリースのため該当なし）

### Deprecated
（初回リリースのため該当なし）

### Removed
（初回リリースのため該当なし）

### Security
- OpenAI API キーや各種トークンは Settings を通じて環境変数から取得する設計。必須トークン未設定の場合は明確に ValueError を送出して早期発見を促す。

### Notes / Known limitations
- OpenAI のレスポンスは JSON mode を期待するが、稀に前後に余計なテキストが含まれる可能性があるため、安全側の復元処理（最外側の {} を抽出）を実装している。ただし全ての不正出力を保証できるわけではない。
- DuckDB のバージョン依存（特に executemany の仕様）に注意。コード中に互換性回避のためのワークアラウンドがある。
- 日付取り扱いはすべて naive な date / datetime（UTC or JST の変換は明示実装）で行う。タイムゾーン混入を避ける設計。
- 堅牢性のため、OpenAI 呼び出し失敗時はフェイルセーフ（スコア 0.0 や該当チャンクスキップ）を採用しているが、運用上は API の可用性や料金に注意が必要。
- ai/news_nlp と ai/regime_detector は内部で独自の _call_openai_api 実装を持ち、相互にプライベート関数を共有しないことでモジュール結合を抑制している。テスト時は各モジュールで該当関数をモック可能。

### Breaking Changes
- なし（初回リリース）

---

貢献者: 実装コードから推測した単一の主要実装者（詳細はリポジトリのコミット履歴を参照してください）

もし CHANGELOG を公開用に整備する場合は、実際のコミットやリリース日・変更差分に合わせて Unreleased → バージョンへ移行・分割してください。必要であれば、各モジュールごとの詳細な変更点（関数シグネチャ、例外挙動、SQL スキーマ想定など）をさらに分解して記載できます。どの粒度で詳述するか指示をください。