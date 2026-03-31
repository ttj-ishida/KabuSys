CHANGELOG
=========
すべての注目すべき変更を記録します。このプロジェクトは Keep a Changelog の慣習に従います。
安定版リリースのみを日付付きで記載しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-31
--------------------

Added
~~~~~

- 基本パッケージを初期リリース
  - パッケージ名: kabusys、バージョン __version__ = 0.1.0
  - 主要モジュールを公開: data, strategy, execution, monitoring

- 環境・設定管理 (kabusys.config)
  - .env および .env.local をプロジェクトルート（.git / pyproject.toml を探索）から自動読み込みする仕組みを実装
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能
  - .env の行パーサを実装（コメント行・export プレフィックス・クォート内のバックスラッシュエスケープ・インラインコメントの扱い等に対応）
  - _load_env_file による保護キー（os 環境変数の上書き防止）や override オプションを実装
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 監視設定 / ログレベル / 実行環境等の取得・バリデーションを提供
    - 必須環境変数が未設定時は ValueError を送出（明確なメッセージ）
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値セット）を実装
    - Path 型でのパス取得・展開をサポート（duckdb/sqlite/pid ファイル等）

- AI モジュール (kabusys.ai)
  - news_nlp
    - raw_news と news_symbols を元にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON mode を使ってセンチメントを算出
    - バッチ処理（デフォルト 20 銘柄／チャンク）、1 銘柄あたり記事数上限・文字数トリムを実装
    - API 呼び出しの再試行（429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ）とフェイルセーフ（失敗時はスキップ）
    - レスポンスの厳密バリデーションとスコアの ±1.0 クリップ処理
    - ai_scores テーブルへの冪等的な差し替え保存（DELETE → INSERT、部分失敗時に他銘柄スコアを保護）
    - calc_news_window ユーティリティ（JST ベースのニュースウィンドウ計算）
    - テスト用に _call_openai_api をモック可能に設計
  - regime_detector
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）と、news_nlp を用いたマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定
    - OpenAI 呼び出しに対する再試行/バックオフ・エラーハンドリングを実装（API 失敗時は macro_sentiment=0.0 のフォールバック）
    - DuckDB を用いた ma200_ratio 計算・raw_news 抽出・market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - ルックアヘッドバイアス回避の設計（date 引数のみを使用し datetime.today() を参照しない）
    - テストのために内部 API コールを差し替えられる設計

- Data / ETL / カレンダー (kabusys.data)
  - calendar_management
    - JPX マーケットカレンダー管理（market_calendar テーブルを用いた営業日判定、SQ 日判定、next/prev/get_trading_days 等）
    - DB にデータがある場合は DB 値優先、未登録日は曜日ベースのフォールバック（堅牢な挙動）
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェック・冪等保存
  - pipeline / ETLResult
    - ETL パイプラインの骨格（差分取得・保存・品質チェックの実行方針をコードに反映）
    - ETLResult dataclass を実装し、実行結果・品質問題・エラーの集約と to_dict による可視化を提供
    - DuckDB を用いたテーブル存在チェックや最大日付取得等のユーティリティ
  - etl モジュールが ETLResult を公開（再エクスポート）

- Research（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、ma200_dev）、ボラティリティ（20 日 ATR）、
      バリュー（PER/ROE）等の定量ファクターを DuckDB SQL ベースで計算する関数を提供
    - データ不足時の None 扱い、結果は (date, code) をキーとする dict のリストで返却
  - feature_exploration
    - 将来リターン計算（任意ホライズン、horizons の検証）と効率的な 1 クエリ取得実装
    - IC（Spearman の ρ）計算、ランク変換（同順位は平均ランク）実装
    - factor_summary による基本統計量（count/mean/std/min/max/median）算出（標準ライブラリのみで実装）
  - 依存軽量設計（pandas 等に依存しない）

- 共通設計・品質
  - DuckDB を中心に設計（ローカル分析・ETL 用に最適化）
  - トランザクションを明示的に使用した冪等処理（BEGIN/COMMIT/ROLLBACK ハンドリング）
  - ルックアヘッドバイアス防止の観点で日時取得を外部から注入する設計（date 引数主体）
  - ロギングと警告メッセージを充実させ、失敗時に例外を投げる箇所とフェイルセーフにする箇所を明確化

Changed
~~~~~~~

- 初期リリースにつき該当なし

Fixed
~~~~~

- 初期リリースにつき該当なし（ただし各所に堅牢化・入力検証・フェイルセーフ実装あり）

Security
~~~~~~~~

- OpenAI API キーや他のシークレットは Settings 経由で環境変数から取得する設計
- .env の自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト・CI 用）

Notes / Implementation Decisions
--------------------------------

- OpenAI の呼び出しはニュース NLP とレジーム判定で JSON Mode を使用し、レスポンスの厳密バリデーションを行う。
- LLM 呼び出し部はテスト容易性を考慮して内部関数をモック可能にしている（例: unittest.mock.patch で差し替え可能）。
- DuckDB の executemany に対する互換性考慮（空リスト不可など）を反映した実装になっている。
- 日時やウィンドウ計算はすべて timezone-naive な date/datetime を使い、JST/UTC 変換を明示的に扱う（ルールとコメントあり）。

--- 

この CHANGELOG はコードの現状から推測してまとめたものです。実際のリリースノートや変更履歴の運用方針に応じて、追記・修正してください。