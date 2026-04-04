CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠しています。
セマンティック バージョニングを採用します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-04
--------------------

Added
- 初回リリース: KabuSys パッケージの基本機能を追加。
  - パッケージエントリポイント:
    - src/kabusys/__init__.py: バージョン情報と公開サブパッケージ (data, strategy, execution, monitoring) を公開。
  - 環境設定管理:
    - src/kabusys/config.py:
      - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
      - .env のパースは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
      - override/protected 機構により、.env.local で OS 環境変数を保護しつつ上書き可能。
      - Settings クラスを提供し、J-Quants / kabu API / LINE / データベースパス / 監視設定 / システム設定（KABUSYS_ENV, LOG_LEVEL）等のプロパティを取得可能。バリデーション機構（有効な env 値・ログレベルチェック）を備える。
      - デフォルトパス: DUCKDB_PATH= data/kabusys.duckdb, SQLITE_PATH= data/monitoring.db など。
  - AI（自然言語処理）:
    - src/kabusys/ai/news_nlp.py:
      - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価を行い ai_scores テーブルに格納する機能を提供。
      - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）、1銘柄あたり記事数制限・文字数トリム、バッチサイズ、再試行（指数バックオフ）処理、応答の検証とスコアクリップ（±1.0）を実装。
      - DuckDB に対して冪等的に DELETE → INSERT を行う実装、部分失敗時に既存データを保護する設計。
      - score_news() を公開 API としてエクスポート。
    - src/kabusys/ai/regime_detector.py:
      - 日次で市場レジーム判定を行う score_regime() を提供。
      - ETF (1321) の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して regime_score / regime_label を market_regime テーブルへ冪等書き込みする。
      - マクロニュース抽出、OpenAI 呼び出し（独自のラッパー）、リトライ/フォールバック（API失敗時は macro_sentiment=0.0）等を実装。
  - Data（データ基盤）:
    - src/kabusys/data/calendar_management.py:
      - JPX カレンダー管理：market_calendar テーブルを参照して営業日判定（is_trading_day, is_sq_day）、前後営業日取得（next_trading_day, prev_trading_day）、期間内営業日リスト取得（get_trading_days）等を実装。
      - カレンダーデータが存在しない場合は曜日ベース（土日非営業）でフォールバック。最大探索日数の上限や健全性チェックを導入。
      - calendar_update_job() により J-Quants から差分取得して冪等に保存（バックフィル / lookahead / sanity チェックあり）。
    - src/kabusys/data/pipeline.py:
      - ETLResult データクラスを導入（ETL 実行メタ情報、品質問題の集約、エラー有無判定など）。
      - 差分更新・バックフィル・品質チェック等の方針を実装（jquants_client 経由の取得 / 保存、品質チェックは収集して呼び出し元へ伝播）。
    - src/kabusys/data/etl.py:
      - pipeline.ETLResult を再エクスポート（外部からの参照用）。
  - Research（リサーチ）:
    - src/kabusys/research/factor_research.py:
      - ファクター計算: calc_momentum, calc_volatility, calc_value を実装。prices_daily/raw_financials を利用してモメンタム、200日移動平均乖離、ATR、流動性、PER/ROE 等を返す。
      - DuckDB 上の SQL + Python による実装で、データ不足時の None 処理等に配慮。
    - src/kabusys/research/feature_exploration.py:
      - 将来リターン計算 (calc_forward_returns)、IC（Spearman）計算 (calc_ic)、ランク (rank)、ファクター統計要約 (factor_summary) を提供。
      - pandas 等に依存せず標準ライブラリで実装。
    - src/kabusys/research/__init__.py:
      - 主要な研究用関数群をエクスポート。
  - その他:
    - src/kabusys/ai/__init__.py: score_news を公開。
    - ロギング、警告出力、DuckDB の制約（executemany の空リスト禁止）への対応など運用上の配慮を多数実装。

Changed
- 初回リリースのため過去バージョンからの変更は無し。

Fixed
- 初回リリースのため過去バージョンからの修正は無し。

Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策:
  - 全ての解析/スコアリング関数は datetime.today() や date.today() などで現在日時を参照せず、呼び出し側から target_date を受け取る設計。
  - DB クエリにも target_date 未満／以前などの排他条件を厳格に適用。
- フェイルセーフ:
  - OpenAI 等の外部API呼び出しでの失敗は局所的に扱い、可能な限り処理を継続（例: macro_sentiment=0.0、スコア未取得はスキップ）し、致命的エラーは上位で取り扱う。
- 冪等性:
  - DB 書き込みは可能な限り冪等（DELETE → INSERT、ON CONFLICT 想定/説明）で実装。
- テスト容易化:
  - OpenAI 呼び出しラッパー関数をモジュール内に設け、テスト時に差し替え可能にしている（unittest.mock.patch を想定）。
- 外部依存:
  - OpenAI（gpt-4o-mini）、J-Quants クライアント、kabuステーション API（設定）を利用する前提。初期設定や API キーの環境変数設定が必要。

今後の予定（例）
- strategy / execution / monitoring サブパッケージの具体実装とテスト充実。
- ai モデル評価のロギング強化とコスト管理。
- ETL/quality モジュールの詳細な品質検出ルール追加。

--- 

注: 実装の詳細は該当するソースファイルの docstring とコメントに従っています。変更履歴はソースコードから推測して記載しています。