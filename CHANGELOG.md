CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
本リポジトリはセマンティックバージョニングに従います。

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-04-03
-------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」の基礎モジュール群を導入。
- パッケージ公開:
  - パッケージルート: kabusys (バージョン 0.1.0)
  - エクスポート: data, strategy, execution, monitoring を __all__ で公開。
- 環境設定管理（kabusys.config）を追加:
  - .env/.env.local からの自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して検出）。
  - .env のパースは export 形式・クォート・エスケープ・インラインコメントを考慮。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - OS 環境変数を保護する protected キーセットの概念に対応。
  - 必須値取得用 _require()、各種設定プロパティを持つ Settings クラスを提供（OpenAI/ J-Quants / kabu API / LINE / DB パス / 監視設定など）。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL 値検証を実装。
- AI モジュール（kabusys.ai）を追加:
  - ニュースNLP（kabusys.ai.news_nlp）:
    - raw_news と news_symbols を集約し、銘柄ごとに GPT 系モデル（gpt-4o-mini）の JSON mode でセンチメントを算出。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に対応する calc_news_window を実装。
    - バッチ処理（最大 20 銘柄/チャンク）、記事数・文字数トリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンス検証ロジック（JSON 抽出、results リスト検証、コード整合性、数値チェック、±1.0 でクリップ）。
    - 書き込み: ai_scores テーブルへ idempotent に DELETE → INSERT（部分失敗時に他銘柄を保護）。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタし、OpenAI（gpt-4o-mini）で JSON レスポンスを解析。
    - API エラー時はフェイルセーフで macro_sentiment=0.0 を採用。
    - レジーム結果を market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で保存。
    - LLM 呼び出しは独立実装としてテスト可能に設計。
- データプラットフォーム（kabusys.data）を追加:
  - カレンダー管理（kabusys.data.calendar_management）:
    - JPX カレンダー（market_calendar）を基に営業日判定、前後営業日取得、期間内営業日リスト取得、SQ日判定を実装。
    - calendar_update_job により J-Quants から差分取得 → 保存（バックフィル、健全性チェック、ON CONFLICT 相当の扱い）を実装。
    - DB にカレンダーがない場合は曜日ベース（土日非営業）でフォールバックする一貫性を提供。
  - ETL パイプラインの基礎（kabusys.data.pipeline / etl）:
    - ETLResult データクラスを公開し、ETL 実行結果（取得/保存数、品質問題、エラー概要）を構造化。
    - 差分更新・バックフィル・品質チェックを想定した設計（J-Quants クライアント連携、保存は idempotent を前提）。
    - _table_exists / _get_max_date 等のユーティリティを実装。
  - etl モジュールで pipeline.ETLResult を再エクスポート。
  - data パッケージのプレースホルダ __init__ を追加。
- 研究用モジュール（kabusys.research）を追加:
  - ファクター計算（kabusys.research.factor_research）:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR）、Liquidity（20 日平均売買代金・出来高比）、Value（PER、ROE）を計算する関数を実装。
    - DuckDB 上で SQL+ウィンドウ関数を用いて効率よく算出。データ不足時の None ハンドリングあり。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - 将来リターン算出（calc_forward_returns: 任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）とランク変換ユーティリティ（ties は平均ランクで処理）。
    - ファクター統計サマリー（count/mean/std/min/max/median）を実装。
  - research パッケージの __init__ で主要関数群を再エクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
- 安全設計・テスト性向上:
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() をスコアリングロジック内部で参照しない設計方針を明示。
  - OpenAI 呼び出し箇所はテストで差し替え可能（patch 対応）。
  - DuckDB の executemany に関する互換性考慮（空パラメータ回避）を反映。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは明示的に引数から注入可能。環境変数 OPENAI_API_KEY 未設定時は ValueError を投げる仕様とし、不正な無名使用を防止。

Notes / Implementation details
- OpenAI: gpt-4o-mini を JSON mode（response_format={"type":"json_object"}）で利用する前提。
- マクロキーワードやパラメータ（MA ウィンドウ, 重み, バッチサイズ, リトライ回数など）はモジュール内定数で定義されており、運用時に調整可能。
- DuckDB をデータ層として利用。テーブル名参照（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等）を前提に実装。
- ログ出力を随所に配置し、フェイルセーフ（API 失敗時のフォールバック）や ROLLBACK の失敗ログなどを考慮。

Authors
- KabuSys 開発チーム（コードベースから推測して作成）

Acknowledgements
- 本 CHANGELOG は提示されたコードベースの内容から推測して作成しました。