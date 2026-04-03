CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし

0.1.0 - 2026-04-03
------------------

Added
- パッケージ初版を公開
  - パッケージメタ:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定、公開サブパッケージとして data, strategy, execution, monitoring を宣言。

- 設定/環境変数管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env/.env.local の読み込み優先順 (OS 環境変数 > .env.local > .env)。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などを考慮したパーサを実装。
    - override / protected オプションにより OS 環境変数の上書きを保護。
    - 必須キー未設定時に ValueError を投げる _require と Settings クラスを提供。J-Quants、kabu API、LINE、DB パス、監視閾値、環境種別（development/paper_trading/live）などのプロパティを提供。
    - ログレベル・環境名のバリデーションを実装（許容値チェック）。

- AI（Natural Language）機能
  - src/kabusys/ai/news_nlp.py
    - ニュース記事から銘柄ごとにセンチメントスコアを算出し ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当）計算、raw_news と news_symbols を結合して銘柄ごとに記事集約。
    - 1銘柄あたり記事数・文字数制限（トリム）を実装し、最大バッチサイズで OpenAI（gpt-4o-mini）へバッチ送信。
    - 429, ネットワーク断, タイムアウト, 5xx などは指数バックオフでリトライ。API 失敗やパース失敗はフェイルセーフで該当チャンクをスキップし続行。
    - JSON レスポンスのバリデーションを実装（"results" リスト、各要素の code/score チェック、数値変換、既知コードのみ受容、スコアの ±1.0 クリップ）。
    - DuckDB への書き込みは冪等（対象コードのみ DELETE → INSERT）で実装し、部分失敗時の既存データ保護を考慮。
    - テスト容易性のため OpenAI 呼び出し関数を内部でラップして差し替え可能にしてある（unittest.mock.patch を想定）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ書き込む処理を実装。
    - prices_daily からの MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを排除。
    - マクロニュースはマクロキーワードでフィルタしてタイトルを抽出し、OpenAI（gpt-4o-mini）でマクロセンチメントを JSON 出力で評価。
    - API エラー時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ。API リトライロジックと 5xx 判定を実装。
    - 最終的なスコアは所定の式で合成・クリップし、冪等に DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - 設計ポリシーとして datetime.today()/date.today() の直接参照を避けルックアヘッドバイアスを防止。

- データ基盤（Data）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理ロジックを実装（market_calendar テーブル参照）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバックする一貫した振る舞いを確保。
    - calendar_update_job を実装（J-Quants API から差分取得 → 保存）。バックフィル、健全性チェック、例外ハンドリングを備える。
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL パイプラインの骨子と結果表現 ETLResult を実装（差分取得、保存、品質チェックのフローを想定）。
    - ETLResult に target_date, 取得/保存件数、品質問題リスト、エラーリストを持ち、has_errors / has_quality_errors / to_dict を提供。
    - DuckDB のテーブル存在チェックや最大日付取得等のヘルパーを実装。
    - jquants_client と quality モジュールを統合する設計（実動作は jquants_client 側実装に依存）。

- リサーチ（Research）
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールを実装。
      - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す設計。
      - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。欠損時は None を許容。
      - calc_value: raw_financials から最新の財務数値を取得して PER/ROE を計算（EPS が 0 または欠損時は PER を None）。
    - DuckDB の SQL ウィンドウ関数を効率的に使用する設計。外部 API にはアクセスしない。
  - src/kabusys/research/feature_exploration.py
    - 研究用ユーティリティを実装。
      - calc_forward_returns: 指定ホライズンの将来リターンを一度のクエリで取得。horizons の検証を実施。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。十分なデータがない場合は None。
      - rank: 同順位は平均ランクを与えるランク関数（丸めで ties 検出を安定化）。
      - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。

- その他
  - モジュール間の結合を抑える設計が随所に採用されており、OpenAI 呼び出し部分はテストで差し替えやすく実装されている（内部ラッパー関数を利用）。
  - ルックアヘッドバイアス防止のため、target_date ベースの計算・クエリ設計（date < target_date / date = target_date 等）を徹底。
  - DuckDB を用いたクエリ実装において、executemany に空リストを渡さない等の互換性配慮が行われている。

Changed
- なし（初版）

Fixed
- なし（初版）

Removed
- なし（初版）

Security
- なし（初版）

Notes
- 本リリースは初期実装（プロトタイプ/アルファ相当）であり、特に OpenAI API 呼び出しや外部 API 依存部分については運用前に十分な検証とキー管理（環境変数の安全な管理）を推奨します。