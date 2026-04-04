# Changelog

すべての変更は Keep a Changelog のガイドラインに準拠して記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース。KabuSys のコア機能群（データ収集/ETL、カレンダー管理、ファクター計算、AI ベースのニュース解析・市場レジーム判定、環境設定ユーティリティなど）を提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョン設定と公開 API（kabusys.__version__ = 0.1.0、__all__ に data, strategy, execution, monitoring を定義）。
- 環境/設定管理 (src/kabusys/config.py)
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートの探索は .git または pyproject.toml を基準に行う）。
  - 読み込みの優先順位は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env の行パース機能を強化（export プレフィックス対応、引用符中のエスケープ、コメントルールの処理など）。
  - 環境変数取得用 Settings クラスを実装。J-Quants / kabuステーション / LINE / DB パス / 監視設定 / ログレベル等のプロパティを提供。
  - env 値および LOG_LEVEL のバリデーション（許容値外は ValueError）。
  - 環境変数保護（読み込み時に既存の OS 環境変数を protected として扱う）を実装。
- データ基盤 (src/kabusys/data)
  - カレンダー管理 (calendar_management.py)
    - market_calendar テーブルを用いた営業日判定 API: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB データが存在しない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - 夜間バッチ calendar_update_job：J-Quants から差分取得して冪等に保存（バックフィルと健全性チェックを含む）。
  - ETL パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスを導入（取得数・保存数・品質問題・エラー一覧などを格納）。
    - 差分取得／バックフィル／品質チェックの設計方針とユーティリティを追加（jquants_client 経由の保存、品質チェックは収集して上位で判断する方針）。
    - data.etl で ETLResult を再エクスポート（公開インターフェース）。
- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news と news_symbols を基にターゲット時間ウィンドウのニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価して ai_scores テーブルへ書き込み。
    - バッチサイズ、1銘柄あたりの最大記事数・文字数制限、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳格なバリデーション、スコアの ±1.0 クリップを実装。
    - calc_news_window 関数で JST ベースのニュースウィンドウ（前日15:00～当日08:30 JST）を計算。
    - テスト容易性のため API 呼び出し関数を差し替え可能に設計（unittest.mock でパッチ可能）。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルへ冪等に書き込み。
    - LLM（gpt-4o-mini, JSON mode）呼び出し、リトライ/バックオフ、API 失敗時のフェイルセーフ（macro_sentiment=0.0）、ロックフリーの DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - レジームは 'bull' / 'neutral' / 'bear' のラベル化、score のクリッピングと閾値定義を提供。
- リサーチ/ファクター (src/kabusys/research)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時の挙動を明示）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を結合して PER, ROE を算出（EPS が 0/欠損の扱いを明記）。
    - DuckDB を用いた SQL＋Python での効率的な実装（外部 API にアクセスしない設計）。
  - feature_exploration.py
    - calc_forward_returns: 指定日から各ホライズンの将来リターンを一括取得（horizons の妥当性チェック）。
    - calc_ic: Spearman（ランク相関）による IC 計算（None や十分なデータがない場合の処理）。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と基本統計量の集計ユーティリティを実装。
  - research.__init__ で主要関数をエクスポート（zscore_normalize は kabusys.data.stats から再利用）。
- その他
  - OpenAI クライアントの初期化は api_key 引数または環境変数 OPENAI_API_KEY を参照する柔軟な解決ロジックを採用。
  - テストを考慮した設計（API 呼び出し部分の差し替え可能性、KABUSYS_DISABLE_AUTO_ENV_LOAD 等）。
  - DuckDB を主要なローカル分析 DB として採用（SQL クエリ中心の処理設計）。

### 変更 (Changed)
- （初版リリースのため該当なし）

### 修正 (Fixed)
- （初版リリースのため該当なし）

### セキュリティ (Security)
- 環境変数の自動ロードは既存 OS 環境変数を保護する設計（.env ファイルの読み込みで既存値を上書きしない既定挙動、.env.local は override 可）。
- API キーの未設定時に明示的な ValueError を投げることで誤った公開呼び出しを防止。

### 既知の設計方針・注意点
- ルックアヘッドバイアス回避のため、日付判定・ウィンドウ計算は datetime.today()/date.today() を内部で参照しない設計（target_date を明示的に渡す）。
- OpenAI 呼び出しは JSON mode を期待するため、応答のパースは厳格。パース失敗時は例外を投げずフェイルセーフ（スコア=0 やスキップ）で継続する。
- DuckDB のバージョン差分に配慮した実装（executemany に空リストを渡さない等）。
- 外部依存は最小限（duckdb, openai）に抑え、外部ワークフロー（発注等）へはこの層でアクセスしない方針。

---

配布・運用時は README や DataPlatform.md / StrategyModel.md の参照により DB スキーマや外部 API（J-Quants, kabuステーション, OpenAI）の前提条件を確認してください。