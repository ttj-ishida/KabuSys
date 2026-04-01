# CHANGELOG

すべての注記は Keep a Changelog の慣例に従っています。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

## [0.1.0] - 2026-04-01

### 追加（Added）
- パッケージ初版を公開。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 基本パッケージ構成を追加。
  - モジュール群: data, research, ai, (strategy, execution, monitoring を意図した公開)
  - エントリポイント: src/kabusys/__init__.py にて __version__ と __all__ を定義。

- 環境設定・ロード機能を実装（src/kabusys/config.py）。
  - .env / .env.local ファイルの自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - export KEY=val 形式やクォート／エスケープ／インラインコメントに対応した行パーサーを実装。
  - OS 環境変数を保護する protected オプションによる上書き制御。
  - Settings クラスでアプリ設定を型安全に取得（必須キー検証・デフォルト値・検証ロジック含む）。
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境モード（development/paper_trading/live）等を提供。

- AI（OpenAI）を用いたニュースNLP と市場レジーム判定を実装（src/kabusys/ai/*）。
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチサイズ、記事数上限、文字数トリム、JSON Mode を利用したレスポンス処理。
    - リトライ（429/ネットワーク/タイムアウト/5xx）・指数バックオフ・レスポンスバリデーション。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - テスト容易性: _call_openai_api をモック差し替え可能。
    - タイムウィンドウ算出 util（calc_news_window）を提供（JST→UTC 変換・半開区間）。
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し、リトライ・フォールバック（失敗時 macro_sentiment=0.0）。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - lookahead バイアス防止のため date < target_date 条件等を厳守。

- データ基盤ユーティリティを追加（src/kabusys/data/*）。
  - calendar_management
    - market_calendar の管理機能（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データが無い場合は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job にて J-Quants から差分取得・バックフィル・健全性チェック・冪等保存（jquants_client を利用）。
  - pipeline / etl
    - ETLResult データクラス（ETL 実行結果の構造化保存・シリアライズ）を提供。
    - pipeline モジュール方針: 差分取得、バックフィル、品質チェック、idempotent 保存（jquants_client 経由）を想定。
    - etl モジュールで ETLResult を公開再エクスポート。

- 研究用ユーティリティを追加（src/kabusys/research/*）。
  - factor_research: calc_momentum, calc_value, calc_volatility
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離など。
    - Value: PER, ROE（raw_financials からの最新財務データ結合）。
    - Volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率等。
    - DuckDB を用いた SQL ベース実装（営業日窓のバッファ等を考慮）。
  - feature_exploration: calc_forward_returns, calc_ic, rank, factor_summary
    - 将来リターンの計算（horizons の検証、単一クエリ実装）。
    - Spearman（ランク相関）による IC 計算、同順位処理、統計サマリー関数。
  - research パッケージ __init__ で主要関数を公開。

### 変更（Changed）
- 初回リリースのため特になし。

### 修正（Fixed）
- 初回リリースのため特になし。

### 注意事項（Notes）
- OpenAI API キーは関数引数で注入可能（api_key 引数）または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出して呼び出し側に明示。
- テスト支援: OpenAI 呼び出し箇所は内部関数をモック可能に設計（ユニットテストでパッチしやすい）。
- DuckDB のバージョン差異（executemany に空リスト不可等）に配慮した実装（空時の分岐）を行っている。
- すべてのモジュールは lookahead バイアスを避ける設計（datetime.today()/date.today() を直接使わない／クエリの排他条件等）。

### 未実装 / 将来の拡張（今後の予定・推測）
- strategy / execution / monitoring の具体実装はこのスナップショットには含まれていないが、パッケージの __all__ では公開予定として示されている。
- J-Quants クライアント（jquants_client）はデータ取得／保存の外部依存として参照されており、実働環境での統合が必要。

---

以上がコードベースから推測した初版（0.1.0）の主な変更点です。必要であれば各モジュールごとの詳細な変更点（関数一覧・挙動の抜粋）を追記できます。どのレベルの詳細が必要か教えてください。