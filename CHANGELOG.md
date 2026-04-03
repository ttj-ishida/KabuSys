CHANGELOG
=========

すべての変更は Keep a Changelog の慣習に従って記載しています。
http://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-03
-------------------

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開。

Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名と __version__="0.1.0" を定義。公開モジュール候補として data, strategy, execution, monitoring を列挙。

- 環境設定管理
  - src/kabusys/config.py:
    - .env/.env.local をプロジェクトルート（.git や pyproject.toml を探索）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export 付き行、シングル/ダブルクォート内のエスケープ、インラインコメント処理などを考慮した .env パーサを実装。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境種別（development/paper_trading/live）などをプロパティ経由で取得。
    - 必須環境変数未設定時に分かりやすい例外を送出する _require を実装。

- AI（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py:
    - raw_news / news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）にバッチで問い合わせて銘柄別センチメント（ai_score）を算出。
    - JSON Mode を想定したレスポンスバリデーション、余分なテキスト混入ケースの復元処理、スコアの ±1.0 クリップを実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装し、失敗時は該当チャンクをスキップ（フェイルセーフ設計）。
    - テスト容易性のため _call_openai_api を分離（モック可能）。
    - calc_news_window: JST 基準のニュース集計ウィンドウ計算ユーティリティを提供。
    - ai_scores テーブルへの冪等書き込み（DELETE → INSERT）処理を実装。部分失敗時に既存データを保護する挙動。

  - src/kabusys/ai/regime_detector.py:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成し、日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news 参照、OpenAI（gpt-4o-mini）にてマクロセンチメントを JSON 出力で取得、スコア合成後 market_regime テーブルへ冪等書き込み。
    - API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフ。
    - OpenAI 呼び出しのためのリトライロジック実装、テスト用モックポイントを提供。
    - ルックアヘッドバイアス対策（target_date 未満のみで計算）を設計方針に明示。

- データ基盤（Data Platform）
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理（market_calendar）用ユーティリティ。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar 未取得時は曜日ベースのフォールバック（週末は非営業日）を使用し、一貫性のある振る舞いを実装。
    - calendar_update_job: J-Quants からの差分取得 → market_calendar への冪等保存フローを実装。バックフィル・健全性チェックを含む。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py:
    - ETL パイプラインの基礎を実装。
    - ETLResult dataclass を導入し、取得/保存件数・品質チェック結果・エラー情報を構造化して返却・シリアライズ可能に。
    - 差分更新・バックフィル・品質チェック・idempotent 保存（jquants_client の save_* を想定）などの設計を反映。
    - _table_exists / _get_max_date 等の内部ユーティリティを実装（DuckDB ベース）。

  - src/kabusys/data/__init__.py:
    - data モジュールの公開ポイント（pipeline.ETLResult を再エクスポート via etl.py）。

- 研究用ユーティリティ（Research）
  - src/kabusys/research/__init__.py:
    - 主要な研究関数をまとめてエクスポート（momentum, volatility, value, zscore_normalize, forward returns, IC, summary, rank）。
  - src/kabusys/research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離（ma200_dev）を計算。データ不足時の扱いを明確化。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。NULL の伝播や窓サイズチェックを実装。
    - calc_value: raw_financials から最新財務を取り出し PER/ROE を計算。対象日における株価との結合を実装。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで計算する効率的実装。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。有効レコードが少ない場合は None を返す。
    - rank: 平均ランク（同順位は平均）を返す補助関数（浮動小数の丸めで ties を扱う）。
    - factor_summary: count/mean/std/min/max/median を返す統計サマリー機能。

- テストを想定した設計上の配慮
  - OpenAI 呼び出しをラップする private 関数（_call_openai_api）を各モジュールに用意し、unittest.mock.patch による差し替えを想定。
  - API エラーやレスポンス不正時に例外を投げずにログ出力してフォールバックする箇所を多く設け、ロバスト性を重視。

Changed
- 初回リリースにつき該当なし（ベース実装の追加のみ）。

Fixed
- 初回リリースにつき該当なし。

Security
- 初回リリースにつき該当なし。

Notes（実装上の重要ポイント）
- DuckDB を主要なストレージレイヤとして利用。SQL ウィンドウ関数や executemany の挙動（空リスト不可など）に配慮した実装。
- OpenAI は gpt-4o-mini を想定。JSON Mode の利用を前提としたレスポンス処理（余分な前後テキストの復元処理含む）。
- ルックアヘッドバイアスを防ぐ設計を徹底（日時計算は target_date ベース、date.today()/datetime.today() を直接参照しない箇所が明示されている）。
- DB 書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT 想定の保存ロジック等）。例外発生時は ROLLBACK を試行し、失敗の際は警告ログを出力。

今後の想定改善点（参考）
- strategy / execution / monitoring の具体的実装（現在は公開候補として __all__ に列挙済み）。
- ai モジュールのモデル切替やローカル推論対応、OpenAI レスポンス形式の追加検証。
- ETL の品質チェック結果に基づく自動アクション（例: アラート/再取得）の実装。
- より詳細な監視 (CPU/MEM/DISK閾値を利用したプロセス監視) と実行制御ロジックの追加。

--- 

この CHANGELOG は、提供されたソースコードの構造・コメント・設計方針から推測して作成しています。必要があれば、リリース日や追加の変更点（実装済みだがここに未記載のモジュール等）を反映して更新します。