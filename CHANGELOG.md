CHANGELOG
=========

このCHANGELOGは「Keep a Changelog」仕様に準拠しており、予測可能で読みやすい変更履歴の管理を目的としています。

[Unreleased]
------------

- 現時点の変更はありません。

[0.1.0] - 2026-03-29
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買・リサーチ基盤のコア実装を追加。
  - パッケージ初期化:
    - src/kabusys/__init__.py を追加し、バージョン情報と公開サブパッケージ（data, research, ai, monitoring, strategy, execution 等）を定義。
  - 環境設定 / ロード:
    - src/kabusys/config.py を追加。
      - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - export 構文やクォートの扱い、インラインコメントの考慮など堅牢な .env パーサを実装。
      - OS 環境変数の上書き制御（protected set）、.env 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
      - 必須環境変数検査用の _require と Settings クラス（J-Quants / kabuステーション / Slack / DB パス / 環境判定 / ログレベルバリデーション等のプロパティ）。
  - AI（NLP）機能:
    - src/kabusys/ai/news_nlp.py
      - raw_news と news_symbols を基にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（ai_score）を算出。
      - バッチ処理（1回最大20銘柄）、文字数制限、JSON mode を利用した厳密な JSON 応答検証。
      - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライとフォールバック（失敗時は該当チャンクをスキップ）。
      - レスポンス検証（results 配列、code の正規化、score の数値性検査、±1.0 クリップ）。
      - ai_scores テーブルへの冪等更新（DELETE → INSERT）を実装。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
      - prices_daily/raw_news 参照、OpenAI 呼び出しに対するリトライ、API 失敗時のフェイルセーフ（macro_sentiment=0.0）。
      - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を提供。
  - Data 管理・ETL:
    - src/kabusys/data/pipeline.py
      - ETLResult データクラスを含む ETL パイプライン基盤（差分取得、保存、品質チェックの処理方針とユーティリティ）。
      - DuckDB 上での最大日付取得やテーブル存在チェックなどのヘルパーを実装。
      - backfill による後出し修正吸収や品質問題の収集方針（Fail-Fast ではなく呼び出し元で判断）。
    - src/kabusys/data/etl.py
      - ETLResult を外部へ再エクスポート。
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー管理機能を実装。
      - 営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）を提供。
      - market_calendar が未取得の場合の曜日ベースフォールバック、DB 登録優先の一貫したロジック。
      - calendar_update_job による J-Quants からの差分取得・バックフィル・保存処理（健全性チェック付き）。
  - Research（ファクター・特徴量）:
    - src/kabusys/research/factor_research.py
      - Momentum, Volatility, Value, Liquidity に関するファクター計算関数を実装:
        - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None を返す）。
        - calc_volatility: 20日 ATR（atr_20, atr_pct）、avg_turnover、volume_ratio。
        - calc_value: raw_financials から最新財務情報を取得して PER, ROE を計算。
      - DuckDB 上の SQL ウィンドウ関数を活用して効率的に計算。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する汎用クエリ実装。
      - calc_ic: Spearman ランク相関（Information Coefficient）を実装（不足データや ties に対応）。
      - rank: 同順位は平均ランクを返すランク変換ユーティリティ（丸めによる ties 検出対策あり）。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出する統計サマリー。
    - src/kabusys/research/__init__.py で主要関数をエクスポート。
  - その他:
    - src/kabusys/ai/__init__.py と src/kabusys/research/__init__.py での公開 API 整備。
    - DuckDB を主要なローカル分析 DB として一貫利用する設計。
    - OpenAI SDK 呼び出し部はモジュールごとに独立実装し、テスト時にモックしやすいよう設計（private 関数の差替え想定）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 外部 API キー（OpenAI 等）は引数で注入可能かつ環境変数から取得する設計。必須キー未設定時は明確な ValueError を送出し誤使用を防止。

Notes / Design highlights
- ルックアヘッドバイアス対策:
  - 各種処理（ニュース集約・スコアリング・レジーム判定・ファクター計算）は datetime.today() や date.today() を内部で直接参照せず、必ず target_date を引数で受け取る設計。
  - DB クエリは target_date 未満／範囲制約を明示して未来データを参照しないように注意。
- 冪等性:
  - DB 書き込み操作は DELETE → INSERT や ON CONFLICT を活用して冪等に更新する方針。
- エラーハンドリング:
  - OpenAI 等外部 API 呼び出しでの一時エラーは指数バックオフでリトライ、致命的でない失敗はフォールバック（0やスキップ）して全体処理を阻害しない設計。
- DuckDB 互換性:
  - executemany を使う際の空配列回避など、DuckDB の既知の挙動に配慮した実装。

Acknowledgements
- このリリースは KabuSys のコアデータ処理、NLP スコアリング、ファクター計算、カレンダー管理、ETL 基盤の基礎を提供します。今後はストラテジー実装、実行（kabu API 連携）、監視・通知機能の追加、CI テスト・ドキュメント整備を進める予定です。