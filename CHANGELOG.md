CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。
タグ付け方針: SemVer 準拠。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-29
-------------------

Added
- 初回公開リリース: KabuSys 日本株自動売買／リサーチ基盤 v0.1.0 を追加。
  - パッケージのルート (src/kabusys/__init__.py) にバージョンと主要サブパッケージの公開シンボルを定義。
    - __version__ = "0.1.0"
    - __all__ = ["data", "strategy", "execution", "monitoring"]

- 環境変数／設定管理 (kabusys.config)
  - .env ファイルと環境変数を統合して読み込む自動ロード実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - OS 環境変数を保護する protected 機能を実装。
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサは以下に対応:
    - 空行/コメント行（#）のスキップ、export KEY=val 形式。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理。
    - クォートなしの行でのインラインコメント処理（スペース直前の # をコメントと判定）。
  - Settings クラスで各種設定プロパティを提供:
    - J-Quants / kabuステーション / Slack トークン等の必須取得メソッド（未設定時は ValueError を送出）。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）や KABUSYS_ENV, LOG_LEVEL の検証と既定値。
    - is_live / is_paper / is_dev の簡易判定ヘルパー。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を基に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode で一括評価して ai_scores テーブルに保存する処理を実装。
    - ニュースウィンドウ（JST基準: 前日 15:00 ～ 当日 08:30）を計算する calc_news_window を提供（UTC naive datetime を返す）。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、記事・文字数トリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密バリデーションとスコアの ±1.0 クリップ、異常時は部分スキップしてフェイルセーフに継続する方針。
    - テスト容易性のため、OpenAI 呼び出し箇所は内部で _call_openai_api として分離し、unittest.mock.patch により差し替え可能。
    - DuckDB 互換性を考慮し、executemany に空リストを渡さない安全実装（部分書き換えで既存データ保護）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF (1321) の 200 日移動平均乖離（重み70%）とニュースベースのマクロセンチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込みする機能を実装。
    - calc_ma200_ratio によるデータ不足ハンドリング（不足時は中立値 1.0 を使用）。
    - マクロニュースは news_nlp.calc_news_window と raw_news から抽出し、OpenAI を使って JSON を返す設計。
    - OpenAI 呼び出しに対するリトライ/バックオフ、API/パース失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT を行い、例外時には ROLLBACK を試みる実装。

- データ基盤 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX マーケットカレンダーの夜間差分更新ジョブ(calendar_update_job) と営業日判定ユーティリティを実装。
    - DB 登録データを優先し、未登録日は曜日（平日）ベースでフォールバックする一貫したロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - 最大探索範囲・バックフィル・健全性チェックを導入して無限ループ／異常データを防止。
    - J-Quants クライアント経由の取得と idempotent な保存（jq.save_market_calendar）呼び出しを想定。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETL の結果を表す ETLResult データクラスを提供（取得件数、保存件数、品質チェック問題、エラー集約など）。
    - 差分更新／バックフィル、品質チェック（quality モジュールとの連携）、DuckDB 最大日付取得などのユーティリティを実装。
    - デフォルトのバックフィル日数や API 取得最小日付（_MIN_DATA_DATE）などの定数を定義。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ／因子分析 (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR・相対ATR）、Liquidity（20日平均売買代金・出来高比率）、Value（PER/ROE）等の定量ファクター計算を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用し効率的に集計。データ不足時は None を返す設計。
  - 特徴量探索ユーティリティ (kabusys.research.feature_exploration)
    - 将来リターン計算 (calc_forward_returns)：任意ホライズン（デフォルト [1,5,21]）で将来終値からのリターンを算出。
    - IC（Information Coefficient）計算 (calc_ic)：Spearman ランク相関を実装（同順位の平均ランク処理）。
    - ランキング補助 (rank)：同順位は平均ランクにする実装（丸めによる ties 対策）。
    - 統計サマリー (factor_summary)：count/mean/std/min/max/median を算出する純粋 Python 実装（pandas 非依存）。
  - 研究パッケージ初期エクスポートに以下を追加:
    - calc_momentum, calc_volatility, calc_value, zscore_normalize（外部 data.stats 経由）, calc_forward_returns, calc_ic, factor_summary, rank

Other notes / 設計方針のハイライト
- ルックアヘッドバイアス対策: 主要な関数（news scoring / regime scoring / factor 計算等）は datetime.today()/date.today() に依存せず、呼び出し側が target_date を明示的に渡す設計。
- フェイルセーフ性: 外部 API 呼び出しエラー時は例外を直接上げずにフォールバック（スコア 0.0、空結果スキップ等）する箇所が多く、部分失敗が全体の停止を引き起こさない設計。
- DuckDB 互換性を考慮した実装: executemany に空パラメータを渡さない等の細かな互換性対応あり。
- テスト容易性: OpenAI 呼び出しを内部関数に抽象化してモック差し替えが容易。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Acknowledgements / 注意
- OpenAI の利用には OPENAI_API_KEY が必要。news_nlp.score_news や regime_detector.score_regime は api_key 引数か環境変数 OPENAI_API_KEY を要求します（未設定時は ValueError）。
- .env の作成時は .env.example を参照することを想定（Settings._require のメッセージ）。
- 本バージョンは初期実装のため、追加のユーティリティ、エラーハンドリングの強化、テストカバレッジ拡充が今後の予定です。