# Changelog

すべての変更は「Keep a Changelog」形式に従い、重要度別に分類しています。  
このファイルはコードベース（初回公開相当）から推測して作成しています。

※バージョン番号はパッケージの __version__（0.1.0）に準拠しています。

全体の方針
- DuckDB を中心としたローカルデータプラットフォーム設計。
- 外部 API（J-Quants / OpenAI / kabuステーション 等）との連携を想定した ETL と夜間ジョブを提供。
- ルックアヘッドバイアス防止のため、内部処理で datetime.today()/date.today() を直接参照しない設計。
- OpenAI 呼び出しは JSON Mode を使用し、堅牢なパース・バリデーションとリトライ実装を実装。
- DB 書き込みは冪等化（DELETE → INSERT / ON CONFLICT 等）を重視。

[0.1.0] - 2026-03-31
Added
- パッケージ基礎
  - kabusys パッケージ初期リリース（__version__ = 0.1.0）。
  - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に準拠してエクスポート）。
- 設定管理（kabusys.config）
  - .env ファイルと環境変数の自動読み込み機能（.env, .env.local の順序と override 挙動）。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により CWD に依存しないロード。
  - export KEY=val 形式、クォートおよびインラインコメントの適切なパース処理を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 必須環境変数取得用ヘルパー (_require) と Settings クラス（J-Quants トークン、kabu API 設定、Slack、DB パス、環境/ログレベル検証等）。
- データプラットフォーム（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・バックフィル方針、品質チェックの収集、ETLResult データクラスの導入（処理概要・エラー/品質情報を保持）。
    - DuckDB のテーブル存在チェック・最大日付取得ユーティリティを実装。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を基にした営業日判定機能（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未取得時は曜日ベースのフォールバック（週末非営業）。
    - カレンダーの夜間更新ジョブ calendar_update_job（J-Quants からの差分取得→保存、バックフィル、健全性チェック）。
    - 最大探索日数やバックフィル、先読み日数などの定数制御。
  - jquants_client 連携想定（fetch/save を use する設計）。
- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いた銘柄毎のニュース集約 → OpenAI（gpt-4o-mini）へバッチ送信。
    - チャンク処理（最大 20 銘柄/回）、記事数と文字数のトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - JSON Mode を用いた厳密なレスポンス期待と、前後余分テキストが混入した場合の復元ロジック（最外の {} 抽出）。
    - レスポンスのバリデーション（results リスト、code/score の存在、既知コードのみ採用、数値チェック）、スコアを ±1.0 にクリップ。
    - エラー耐性: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、失敗時は個別チャンクをスキップして継続。
    - DuckDB に対する安全な置換ロジック（部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT）。
    - テスト容易性: OpenAI 呼び出し関数をモジュール内で分離し patch で差し替え可能に実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離を主要指標とし（重み 70%）、マクロニュースの LLM センチメント（重み 30%）と合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news からデータ取得、OpenAI でマクロセンチメント算出（gpt-4o-mini、JSON Mode）。
    - API 障害時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。レスポンスパース失敗や API エラーに対しても安全に継続。
    - 判定結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
- リサーチ（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン）、200 日 MA 乖離、ATR（20日）、流動性指標（20日平均売買代金・出来高比）などの定量ファクター計算関数（calc_momentum, calc_volatility, calc_value）。
    - raw_financials から最新財務データを取得して PER / ROE を計算。データ不足時は None を返す。
    - DuckDB SQL を多用し高効率に計算。結果は (date, code) を含む dict のリストで返却。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）で LEAD を用いて一括取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関の実装（rank ユーティリティを付属）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
- 公開 API/ユーティリティ
  - kabusys.data.etl から ETLResult を再エクスポート。
  - AI モジュールの score_news / score_regime といったパブリック関数を提供。

Changed
- （初回リリースのため該当なし。実装設計上の要点を記載）
  - OpenAI 呼び出しは JSON mode を前提とした厳格なパースとエラーハンドリングを実装。
  - DB 書き込みの互換性を考慮して duckdb.executemany の空リスト扱いに対する防御を追加。

Fixed
- （初回リリースのため該当なし。コード中にログ・RBAC周りの警告/防御を実装）

Security
- 環境変数ロード時に OS 環境変数を保護する protected 引数を導入し、.env.local の上書きでも OS 側のキーを上書きしない仕組みを実装。
- 必須トークン（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）に対する明示的チェック（Settings 内で _require）を提供。未設定時は ValueError を投げるため運用ミスを早期発見可能。

Notes / 使用上の注意
- ルックアヘッドバイアス回避のため、各スコアリング・リサーチ関数は target_date を明示的に受け取り、内部で現在日時を直接参照しません。バッチ処理では target_date を明示的に指定してください。
- OpenAI API の呼び出しは外部キー（OPENAI_API_KEY）を利用します。テスト時は各モジュールの _call_openai_api 関数を unittest.mock.patch 等で差し替えてください。
- DuckDB のバージョン依存性（executemany の空リスト扱いなど）に配慮した実装がされていますが、運用環境の DuckDB バージョンで問題がないか確認してください。
- calendar_update_job・ETL パイプラインは J-Quants クライアント実装（jq.fetch_market_calendar / jq.save_market_calendar 等）に依存します。実運用前に該当クライアント実装と権限設定を確認してください。

今後の候補タスク（推測）
- モデル・戦略（strategy）と発注（execution）モジュールの具体実装（現状パッケージ構成に含まれるが詳細未表示）。
- モニタリング用の DB 書き込み／Slack 通知フロー（Settings に Slack 設定あり）。
- テストカバレッジの強化（外部 API のモックや DuckDB のテストフィクスチャ）。
- ai モジュールでのモデル切替やトークン消費最適化（トークン制限考慮のプロンプト最適化等）。

--- 
（この CHANGELOG はコードから推測して作成した初回リリースの要約です。実際のリリース履歴や日付・細部は運用に合わせて修正してください。）