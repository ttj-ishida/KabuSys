CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
本ファイルはコードベースから推測して自動生成した初期の変更履歴です。実際のリリースノート作成時は適宜調整してください。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-09
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ:
    - src/kabusys/__init__.py に __version__ = "0.1.0"、および公開モジュール一覧を定義（data, strategy, execution, monitoring）。

- 環境設定管理:
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを追加。読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - 独自の .env パーサを実装。export 表記、クォート内のエスケープ、インラインコメントの取り扱いなどを考慮した堅牢なパース。
    - _load_env_file により OS 環境変数を保護する protected 機能を実装（.env.local が override）。
    - Settings クラスを実装し、アプリケーション設定値をプロパティ経由で取得可能に:
      - J-Quants / kabu API / LINE Messaging / DB パス（DuckDB / SQLite） / Paper Trading 設定（PAPER_FILL_MODE 等） / 監視系設定（PID ファイル等） / システム環境（KABUSYS_ENV, LOG_LEVEL）など。
    - 設定値のバリデーション（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）と既定値を提供。
    - 環境変数未設定時に明示的にエラーを投げる _require を実装（必須キー取得時）。

- AI（自然言語処理）:
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
    - 前日 15:00 JST ～ 当日 08:30 JST に相当するニュースウィンドウ計算関数 calc_news_window を提供。
    - 記事の銘柄別集約、1銘柄あたりの記事数・文字数トリム、最大バッチサイズでの API バッチ送信をサポート。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフの再試行を実装。
    - OpenAI レスポンスの厳格な検証（JSON 抽出、results 構造、スコア数値正当性、未知コード除外）を実装し、不整合時は安全にスキップ。
    - スコアは ±1.0 にクリップ。部分成功時の DB 書き換えは対象コードのみに限定（DELETE → INSERT の方式）し既存データ保護。
    - テストを想定した _call_openai_api の差し替えポイントを用意。

  - src/kabusys/ai/regime_detector.py
    - 市場レジーム判定機能を実装（score_regime）。
      - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を組み合わせて日次のレジーム（"bull"/"neutral"/"bear"）を算出。
      - DuckDB の prices_daily / raw_news / market_regime を参照。計算はルックアヘッドバイアスを防ぐ設計（target_date 未満のデータのみ使用、datetime.today() を参照しない）。
      - マクロセンチメントは gpt-4o-mini を JSON 出力モードで呼び出し、最大 20 件のマクロ関連記事タイトルを入力。API エラーやパース失敗はフェイルセーフで macro_sentiment=0.0 にフォールバック。
      - レジームの合成、ラベリング、そして market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - OpenAI 呼び出しの再試行（Retry）とエラー判定を備える。テスト用に _call_openai_apiを差し替え可能。

  - src/kabusys/ai/__init__.py
    - score_news を公開（__all__ に含める）。

- データ関連（Data Platform）:
  - src/kabusys/data/calendar_management.py
    - JPX（市場）カレンダー管理を実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティを提供。
      - market_calendar テーブルが存在しない場合は曜日ベース（土日除外）でフォールバック。DB 登録がある場合は DB 値優先で未登録日は曜日フォールバック（next/prev と一貫）。
      - calendar_update_job を実装し、J-Quants API 経由で差分取得・冪等保存（fetch/save の呼び出しとエラーハンドリング）を行う。バックフィルや健全性チェックを実装。
      - DuckDB を前提とした日付変換ユーティリティ、テーブル存在チェックを実装。

  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基盤実装。
      - 差分更新とバックフィルの方針、品質チェック連携の設計をコメントで明記。
      - ETLResult dataclass を実装（target_date, fetched/saved 件数、quality_issues, errors 等を集約）。
      - ETLResult に has_errors / has_quality_errors / to_dict を実装（監査ログや外部連携向けに変換）。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。

  - その他:
    - src/kabusys/data/__init__.py を追加（パッケージ初期化）。
    - jquants_client / quality 等外部モジュール呼び出し点を設置（実装は別モジュール想定）。

- リサーチ／因子分析:
  - src/kabusys/research/factor_research.py
    - ファクター計算（Momentum / Value / Volatility / Liquidity）を実装:
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日MA乖離）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio 等（ATR 計算で prev_close の NULL 伝播を制御）
      - calc_value: latest 財務情報（raw_financials）と価格を組み合わせて PER / ROE を算出
    - DuckDB の SQL ウィンドウ関数を活用し、データ不足時は None を返す堅牢な実装。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、factor_summary を実装。
      - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）に対する将来リターンを一括取得する SQL 実装。
      - calc_ic: スピアマン（ランク相関）を手計算で実装し、同順位の取り扱い（平均ランク）をサポート。
      - rank: 値の丸めを行った上で同順位に平均ランクを割り当てる実装。
      - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - src/kabusys/research/__init__.py
    - 主要関数（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を公開。

Quality / Design Notes
- ルックアヘッドバイアス防止: AI スコアリング系（news_nlp, regime_detector）およびリサーチ系は内部で datetime.today()/date.today() を直接参照しない設計。すべて target_date を明示的に受け取り、クエリでは排他条件（< target_date 等）を用いる。
- フェイルセーフ: OpenAI API の失敗やパースエラーは基本的に例外を投げずフェールバック（例: macro_sentiment=0.0、スコアスキップ）する設計。
- テスト容易性:
  - AI モジュール内の _call_openai_api を patch 可能にしユニットテストでのモックを想定。
  - 環境変数自動読み込みをテスト時に無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - API キーは関数引数で注入可能（api_key 引数）でテストの独立性を確保。
- DB 互換性: DuckDB (バージョン差分に注意) を考慮した実装（executemany の空リスト回避等）。

Known limitations / Notes
- OpenAI / J-Quants / kabu station 等外部 API のクライアント実装は本差分の範囲外（呼び出し点は用意されているが、実際のクライアント実装は別モジュールまたは外部依存）。
- strategy / execution / monitoring パッケージは __all__ に含まれるが、この差分には具体的実装ファイルが含まれていないためリリース時には別途実装が必要。
- 一部の機能（PBR・配当利回り等）は現バージョンで未実装（コメントで明示）。

Migrating to 0.1.0
- 環境: .env/.env.local に必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY など）を設定してください。
- 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは JSON mode（response_format={"type": "json_object"}）を前提としているため、利用する SDK とレスポンス形状の互換性に注意してください。

Contact / Contributions
- このCHANGELOG はコードから推測して自動生成したものです。誤りや追加情報は README や実装コメントを参照のうえ適宜更新してください。