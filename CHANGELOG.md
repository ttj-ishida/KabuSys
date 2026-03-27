Keep a Changelog
=================

すべての注目すべき変更点をここに記載します。  
このプロジェクトはセマンティック バージョニングに従います。 詳細は https://semver.org/ を参照してください。

[0.1.0] - 2026-03-27
-------------------

初回リリース。

Added
- パッケージ基盤
  - src/kabusys/__init__.py によるパッケージ公開（__version__ = 0.1.0、サブパッケージ data/ strategy/ execution/ monitoring を __all__ でエクスポート）。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みする仕組みを追加。
    - 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサーは export フォーマット、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱いをサポート。
    - OS 環境変数を保護するための protected 上書き制御と override 挙動をサポート。
    - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / システム環境（env, log_level）等のプロパティを型付きで取得・検証（不正値は ValueError）。
    - デフォルトパス（duckdb/sqlite）や有効な環境値セット（development/paper_trading/live）を定義。

- AI 関連
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄別センチメントを算出して ai_scores テーブルに書き込む機能を追加（score_news）。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を calc_news_window で実装。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）によりトークン肥大化を抑制。
    - API 呼び出し時のリトライ（429・ネットワーク・タイムアウト・5xx）と指数バックオフを実装。失敗時は個別チャンクをスキップして処理継続（フェイルセーフ）。
    - レスポンス検証（JSON パース、results リスト、code/score の存在、既知コードフィルタ、数値性チェック）を厳密に行い、スコアは ±1.0 にクリップ。
    - DB への書き込みは部分置換戦略（DELETE for code → INSERT）で冪等性と部分失敗時のデータ保護を確保。DuckDB 互換性（executemany の空リスト回避）に配慮。
    - テスト容易性: OpenAI 呼び出しを _call_openai_api 経由にして unittest.mock.patch により差し替え可能。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュース由来の LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する機能を追加（score_regime）。
    - ma200_ratio の計算は target_date 未満のデータのみを用いることでルックアヘッドバイアスを防止。
    - マクロニュースは news_nlp の calc_news_window を利用してフィルタ、LLM（gpt-4o-mini）で JSON レスポンスを期待。API 失敗時は macro_sentiment=0.0 にフォールバックして継続（フェイルセーフ）。
    - レジームスコア合成、閾値によるラベリング、market_regime への冪等書込（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - OpenAI 呼び出し実装は news_nlp と独立しており、モジュール結合を避ける設計。こちらも _call_openai_api をテスト差し替え可能。

- データプラットフォーム（Data）
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダーを扱うユーティリティを追加。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未導入のケースでは曜日（平日）ベースのフォールバックを行い、DB 登録値がある場合はそれを優先する一貫したロジックを実現。
    - calendar_update_job を実装し、J-Quants API（jquants_client）からの差分取得・バックフィル・健全性チェック（将来日付の過度なずれ検出）・保存処理を行う。保存は idempotent を想定。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL 処理の骨格を実装。差分更新のための最終日取得、API 取得 → 保存（jquants_client の save_* を利用）→ 品質チェック（quality モジュール）という方針を記載。
    - ETLResult データクラスを実装（取得数/保存数/品質問題/エラー一覧などを保持）。to_dict により監査ログ出力向けの辞書化をサポート。
    - デフォルトの backfill や calendar lookahead 等の定数を定義。

  - その他
    - DuckDB を主なデータ格納・クエリ基盤とする実装方針。SQL 内でウィンドウ関数等を活用。
    - jquants_client（外部モジュール）を呼び出す設計を採用。

- リサーチ（研究用解析）
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ／流動性、バリュー（PER, ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - prices_daily と raw_financials のみ参照し、外部 API へのアクセスは行わない（研究環境の安全性）。
    - ma200_dev の未満データや ATR の欠損時は None を返す等、欠損制御を実装。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリ（factor_summary）を追加。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB で動作することを目標に実装。
    - calc_ic はスピアマン（ランク相関）を実装し、有効サンプルが 3 件未満の場合は None を返すなどの安全策を用意。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 実装上の設計判断（重要事項）
- ルックアヘッドバイアス対策
  - AI スコア算出やレジーム判定等、すべての関数が datetime.today() や date.today() を内部で参照しないよう設計。必ず caller が target_date を渡すことで将来データの参照（ルックアヘッド）を防止。
- フェイルセーフ設計
  - 外部 API（OpenAI / J-Quants）障害時は例外で即中断せず、可能な限りフォールバック（macro_sentiment=0.0、チャンクスキップ等）して処理を継続する設計。
- テスト容易性
  - OpenAI 呼び出し等はモジュール内の関数（_call_openai_api 等）を経由しており、unittest.mock.patch による差し替えでテスト可能。
- DuckDB 互換性
  - executemany に空リストを渡せない等の DuckDB（0.10）特性へ配慮した実装（空チェックを明示）。
- DB 書込は冪等化
  - market_regime / ai_scores 等への書き込みは DELETE → INSERT や ON CONFLICT 相当の置換を採用し、部分失敗時に既存データを不必要に削除しない工夫を行っている。

今後のTODO（想定）
- Strategy / Execution / Monitoring サブパッケージの具体的実装（初期公開では未掲載）。
- J-Quants / kabu ステーション向けクライアント実装の補足（jquants_client は依存対象）。
- 単体テスト・統合テストの充実（現状はテスト差し替え用フックを用意済み）。

-----