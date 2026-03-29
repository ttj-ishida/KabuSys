CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。セマンティックバージョニングを採用しています。

Unreleased
----------
- 今後の予定（実装例をコードから推測）
  - strategy / execution / monitoring の具体的な実装追加（現在パッケージ __all__ に名前はあるが実体は未提供）
  - テストカバレッジ拡充（OpenAI 呼び出しのモックを用いたユニットテスト等）
  - 追加ファクター（PBR、配当利回りなど）の実装
  - 秘密情報・API キー取り扱いの改善（Vault サポートなど）
  - ドキュメント整備（API リファレンス、運用ガイド）

[0.1.0] - 2026-03-29
--------------------
Added
- パッケージ初期リリース (kabusys v0.1.0)
  - src/kabusys/__init__.py
    - パッケージ公開名とバージョンを定義（__version__ = "0.1.0"）。
    - public モジュール一覧に data, strategy, execution, monitoring を含める構成。
- 環境設定・ロード機能
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込むユーティリティを実装。
    - プロジェクトルートの自動検出ロジック（.git または pyproject.toml を基準）。
    - .env の行パーサを実装（export プレフィックス、クォート/エスケープ、インラインコメント対応）。
    - 自動ロードの優先順を定義: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 必須変数チェック用の _require と Settings クラスを提供（J-Quants, kabu, Slack, DB パス, 環境判定など）。
    - KABUSYS_ENV と LOG_LEVEL の値検証ロジック、is_live / is_paper / is_dev の便宜プロパティ。
- AI 関連
  - src/kabusys/ai/news_nlp.py
    - ニュースを銘柄単位に集約し OpenAI（gpt-4o-mini）の JSON モードでセンチメント評価を行い ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST 相当の UTC ウィンドウ）。
    - チャンク送信（最大 20 銘柄/リクエスト）、記事・文字数上限（記事数 10 件、文字数 3000 文字）でトリム。
    - リトライ・バックオフ（429、接続障害、タイムアウト、5xx）とフェイルセーフ（失敗時はスキップして継続）。
    - レスポンスの厳格バリデーション（JSON 抽出、results 配列、既知コードチェック、スコア型検証、±1.0 でクリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT）で部分失敗時に既存データを保護。
  - src/kabusys/ai/regime_detector.py
    - ETF (1321) の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）を行い market_regime テーブルへ保存。
    - ma200_ratio 計算（target_date 未満のデータのみ使用してルックアヘッド防止）、マクロ記事フィルタ（キーワードリスト）取得。
    - OpenAI 呼び出しは専用の内部関数で行い、リトライ・5xx ハンドリング・パース失敗時は 0.0 にフォールバック（フェイルセーフ）。
    - DB 書き込みはトランザクションで冪等（BEGIN / DELETE / INSERT / COMMIT）。
- データプラットフォーム関連
  - src/kabusys/data/calendar_management.py
    - market_calendar テーブルを利用した営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar 未取得時の曜日ベースフォールバック（週末を休場とする）を用意し、DB にデータがある場合は DB 値優先。
    - calendar_update_job: J-Quants API クライアント経由でカレンダー差分を取得し冪等保存。バックフィルや健全性チェックを実装。
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの設計とユーティリティを実装。
    - 差分取得、保存（jquants_client 経由、idempotent 保存）、品質チェックの統合を前提。
  - src/kabusys/data/etl.py
    - ETLResult を再エクスポート（pipeline.ETLResult）。
  - src/kabusys/data/pipeline.py（続き）
    - ETLResult dataclass を実装（取得/保存件数、品質問題リスト、エラーリスト、ヘルパープロパティ、辞書変換）。
    - _table_exists / _get_max_date 等の内部ユーティリティを実装。
    - 市場カレンダー補正ヘルパー等を実装。
- リサーチ（研究）モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB の prices_daily / raw_financials を参照して計算する機能を提供。
    - 欠損・データ不足に対して None を返す設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（calc_ic）計算、rank（同順位は平均ランク）および基本統計量を返す factor_summary を実装。
    - Pandas 等に依存せず標準ライブラリ + DuckDB SQL で実装。
  - src/kabusys/research/__init__.py
    - 主要関数を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize など）。
- 実装設計上の特徴（全体）
  - DuckDB をローカル分析 DB として利用する想定（多くの関数は DuckDB 接続を第一引数に取る）。
  - ルックアヘッドバイアス回避方針が徹底されている（datetime.today()/date.today() を直接参照しない設計、クエリで date < target_date や date = ? を利用）。
  - OpenAI 呼び出しに対してモック差し替えがしやすい設計を採用（モジュール内 _call_openai_api を patch 可能）。
  - API 呼び出しのリトライ・指数バックオフ、HTTP 5xx の扱い、フェイルセーフ（失敗時にゼロフォールバックやスキップ）を各所で実装。
  - DB 書き込みは冪等性に配慮（DELETE→INSERT、ON CONFLICT や個別 executemany を活用）。DuckDB 互換性に注意した実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Notes / 既知の制限
- monitoring / execution / strategy の公開名は定義されているが、実体の提供は限定的。今後の実装が必要。
- news_nlp と regime_detector は OpenAI API（gpt-4o-mini, JSON mode）に依存しており、API 仕様の変更や利用制限により挙動が影響を受ける可能性がある。
- DuckDB executemany は空リストを受け付けないため、空チェックを挟む実装がある。DuckDB バージョン差異に注意。
- raw_financials に PBR / 配当利回り等の項目は現バージョンでは未実装。

作者
----
- コード中のドキュメントと設計コメントに基づき、自動生成的に CHANGELOG を作成しました。実際の変更履歴・リリースノートは実開発履歴に合わせて調整してください。