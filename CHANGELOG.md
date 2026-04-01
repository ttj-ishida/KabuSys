CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージ内部の __version__ に合わせています。

[Unreleased]
-------------

（現時点のコードベースは初期バージョンとしてリリース済みのため、Unreleased に特別な差分はありません。）

[0.1.0] - 2026-04-01
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
    - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で公開。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env ファイル（.env, .env.local）および OS 環境変数から設定を自動ロードする機能を追加。
      - プロジェクトルート検出は __file__ を基準に .git または pyproject.toml を探索するため、CWD に依存しない実装。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
      - .env の読み込みルール:
        - export KEY=val 形式に対応
        - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応
        - クォート無しの場合は '#' の直前が空白/タブであればインラインコメントとみなす
      - override / protected パラメータにより OS 環境変数を保護する動作を実装。
    - Settings クラスを提供（settings インスタンスを公開）。
      - J-Quants / kabuステーション / Slack / DB / 監視閾値 / システム環境 などのプロパティを用意。
      - 必須環境変数は _require() で検証し未設定時は ValueError を投げる。
      - KABUSYS_ENV の値検証（development/paper_trading/live）および LOG_LEVEL の検証を実装。
      - パス系設定（duckdb/sqlite/pid）は Path 型で返す。
      - is_live / is_paper / is_dev ヘルパーを追加。

- AI（自然言語）モジュール
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を集約して OpenAI (gpt-4o-mini, JSON mode) でセンチメント分析し ai_scores テーブルへ書き込む機能を実装。
    - 主な機能・設計:
      - JST ベースのタイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供。
      - news_symbols 経由で銘柄ごとに記事を集約し、1銘柄あたり最大記事数・最大文字数でトリム。
      - 1 API コールで最大 20 銘柄をバッチ処理（_BATCH_SIZE）。
      - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
      - レスポンスの厳密な JSON バリデーションとスコアの ±1.0 クリップ。
      - 部分失敗に備え、ai_scores への書き込みは対象コードのみ DELETE → INSERT で置換（冪等性と既存データ保護）。
      - テスト容易性のため OpenAI 呼び出し関数を差し替えられる設計（内部で _call_openai_api 参照）。
      - API キー注入（api_key 引数または環境変数 OPENAI_API_KEY）。
      - フェイルセーフ: API 失敗時は個別チャンクをスキップして残りを継続。最終的に書き込み件数を返す。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull / neutral / bear）を判定する機能を実装。
    - 主な機能・設計:
      - prices_daily から 1321 の過去データを用いて ma200_ratio を計算（target_date 未満のデータのみ使用しルックアヘッドを防止）。
      - raw_news からマクロキーワードでフィルタしたタイトルを抽出し、OpenAI に投げて macro_sentiment を取得。
      - スコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。
      - しきい値に応じて regime_label を決定し market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - API 呼び出し失敗時は macro_sentiment=0.0 として処理を継続（フェイルセーフ）。
      - テスト用に OpenAI 呼び出しを差し替え可能（_call_openai_api）。
      - 定数化されたモデル名（gpt-4o-mini）、最大リトライ、バックオフなどを明確化。

- リサーチ（因子計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - ファクター群を提供（momemtum / volatility / value / liquidity の基本実装）。
      - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。データ不足時の扱いを明確化（None 応答、ログ出力）。
      - calc_volatility: 20 日 ATR（true range の NULL 伝播制御）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials から直近の財務データを取得して PER（EPS が無効時は None）、ROE を計算。PBR/配当利回りは未実装として明記。
    - DuckDB 上の SQL ウィンドウ関数を活用した効率的な実装。
    - 全関数は prices_daily / raw_financials テーブルのみを参照し、本番発注 API にはアクセスしない設計。
  - src/kabusys/research/feature_exploration.py
    - 研究用ユーティリティを提供。
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）での将来リターンを一度の SQL で取得する実装。horizons の入力検証あり。
      - calc_ic: スピアマンランク相関（Information Coefficient）を実装。データ不足（有効レコード < 3）時は None を返す。
      - rank: 同順位は平均ランクを与える実装（丸めで ties を検出する工夫あり）。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算するユーティリティ。
    - pandas 等の外部依存を用いず標準ライブラリで実装。

- データプラットフォーム（ETL / カレンダー / パイプライン）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理機能を実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - market_calendar テーブルの有無に応じた挙動:
        - DB 登録あり: DB 値を優先。未登録日は曜日ベースのフォールバック。
        - DB 未登録時: 曜日ベースのフォールバック（週末を非営業日扱い）。
      - 最大探索日数制限（_MAX_SEARCH_DAYS）を設けて無限ループを防止。
      - calendar_update_job にて J-Quants API からの差分取得 → jq.save_market_calendar で冪等的保存。バックフィルと健全性チェックを実装。
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基盤機能を実装。
      - ETLResult dataclass を定義（取得件数 / 保存件数 / 品質チェック / エラー一覧などを保持）。
      - 差分更新・バックフィル方針・品質チェック（quality モジュールとの連携）等の設計を反映。
      - internal ユーティリティ: テーブル存在チェック、最大日付取得など。
    - src/kabusys/data/etl.py で ETLResult を公開（再エクスポート）。
  - data モジュールは jquants_client（jquants_client を想定）との連携ポイントを用意。

- インフラ／運用関連
  - 設定で監視閾値（CPU/MEM/DISK）や pid ファイルパスを取得可能にし、monitoring 系と連携できる設計を用意。
  - DuckDB を主要な内部 DB として使用。SQL 実行時の互換性（DuckDB 0.10 の executemany 空リスト制約など）を考慮した実装。

Changed
- 初版リリースのため、変更履歴は追加のみ。将来のバージョンで変更点を記載予定。

Fixed
- 初回リリース — 特定のバグ修正履歴は無し（以降のリリースで追記予定）。

Removed
- なし

Security
- なし

Notes / Known limitations
- news_nlp / regime_detector ともに OpenAI (gpt-4o-mini) の JSON mode を使用する設計。ただし外部 API の応答は不安定になる可能性があるため、レスポンスパース失敗時は該当チャンクをスキップしシステム全体は継続するフェイルセーフを採用している。
- calc_value では PBR や配当利回りは未実装（将来の拡張予定）。
- DuckDB のバージョン差異による挙動（リスト型バインドや executemany の制約）を考慮したワークアラウンドが導入されている。
- タイムゾーンは明示的に UTC naive datetime を用いる実装が多く、JST→UTC の変換ルールを内部で扱っている（calc_news_window 等）。
- テスト容易性を考慮し、OpenAI 呼び出し部分はモック差し替えポイントを提供している（ユニットテストでの API 呼び出し回避が容易）。

今後の予定（例）
- PBR / 配当利回り等バリューファクターの拡張。
- monitoring／execution 周りの実装拡充（本リリースでは設定と基盤のみ）。
- テストカバレッジの拡大とエンドツーエンドの QA。

--- 
（この CHANGELOG はソースコードの実装内容から推測して自動的に作成しています。実際のリリースノートは必要に応じて運用チームが追記・修正してください。）