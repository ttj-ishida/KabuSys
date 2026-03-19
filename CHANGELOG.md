# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従います。  
このプロジェクトではセマンティックバージョニングを採用しています。  

リンク: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-19

Added
- 基本パッケージ初期実装を追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
  - パブリック API のエクスポート: `data`, `strategy`, `execution`, `monitoring`
- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込み（自動ロード）。読み込み順は OS 環境変数 ＞ .env.local ＞ .env。
  - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`
  - プロジェクトルート検出ロジック: `.git` または `pyproject.toml` を起点に探索（CWD 非依存）。
  - .env パーサ実装: `export KEY=val` 形式対応、シングル/ダブルクォート中のバックスラッシュエスケープ対応、インラインコメントの取り扱い等を行う `_parse_env_line`。
  - 必須設定の取得ヘルパ: `_require()`（未定義時は ValueError を送出）。
  - `Settings` クラスでのプロパティ化された設定取得:
    - J-Quants / kabu API / Slack / DB パス（DuckDB / SQLite）などの設定を用意。
    - `KABUSYS_ENV` の検証（`development`, `paper_trading`, `live` のみ許容）。
    - `LOG_LEVEL` の検証（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`）。
    - `is_live` / `is_paper` / `is_dev` ヘルパを提供。
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装
    - 固定間隔レート制御（120 req/min）を行う `_RateLimiter`。
    - 再試行ロジック（指数バックオフ、最大 3 回）および 408/429/5xx のリトライ対応。
    - 401 Unauthorized 受信時の自動トークンリフレッシュを 1 回だけ行う仕組み。
    - ページネーション対応（pagination_key を用いたループ取得）。
    - fetch_* 系関数:
      - `fetch_daily_quotes`（日足取得）
      - `fetch_financial_statements`（財務データ取得）
      - `fetch_market_calendar`（JPX カレンダー取得）
    - DuckDB 保存関数（冪等）
      - `save_daily_quotes` -> `raw_prices`（ON CONFLICT DO UPDATE）
      - `save_financial_statements` -> `raw_financials`（ON CONFLICT DO UPDATE）
      - `save_market_calendar` -> `market_calendar`（ON CONFLICT DO UPDATE）
    - 入力値処理ユーティリティ: `_to_float`, `_to_int`（安全に None を返す等の挙動）
    - トークンキャッシュと取得ヘルパ: `get_id_token`（refresh token による取得）
    - 取得時のメタ情報として UTC の `fetched_at` を付与（ルックアヘッドバイアスのトレース用）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を取得して `raw_news` へ保存する基盤を実装
    - デフォルト RSS ソース定義（例: Yahoo Finance のカテゴリ RSS）
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント除去、クエリソート）
    - 記事 ID は正規化 URL の SHA-256（先頭 N 文字）を用いる方針（冪等性確保）
    - XML パースに defusedxml を利用（XML Bomb 等の防御）
    - HTTP 応答サイズ上限（10 MB）や SSRF 対策（スキーム制限・ホスト検証等）を考慮する設計
    - バルク INSERT のチャンク処理とトランザクションまとめ保存、挿入件数の正確取得
- 研究用モジュール（kabusys.research）
  - factor_research:
    - `calc_momentum`（1M/3M/6M リターン、MA200 乖離などを計算）
    - `calc_volatility`（20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等）
    - `calc_value`（PER、ROE を計算。最新財務データを raw_financials から参照）
    - DuckDB のウィンドウ関数を活用し、営業日欠損（祝日・週末）に対応するスキャン範囲バッファを導入
  - feature_exploration:
    - `calc_forward_returns`（与えたホライズンに対する将来リターンを LEAD を用いて一度に取得）
    - `calc_ic`（Spearman の ρ をランク化して計算、サンプル不足時は None を返す）
    - `factor_summary`（count, mean, std, min, max, median を算出）
    - `rank`（同順位は平均ランク、丸めによる ties 対策に round(..., 12) を適用）
  - research パッケージの公開 API まとめ（`__all__` に主要関数を列挙）
- 戦略層（kabusys.strategy）
  - feature_engineering:
    - `build_features(conn, target_date)` 実装
      - research のファクター計算（momentum/volatility/value）を取得し統合
      - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用
      - 数値ファクターを Z スコアで正規化（kabusys.data.stats の zscore_normalize を使用）し ±3 でクリップ
      - features テーブルへ日付単位での置換（DELETE + INSERT をトランザクション内で実行し原子性を保証）
  - signal_generator:
    - `generate_signals(conn, target_date, threshold=0.60, weights=None)` 実装
      - features と ai_scores を統合して各種コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
      - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完するポリシー
      - デフォルト重みは StrategyModel.md に基づく。ユーザ指定重みは検証・補完・リスケールされる。
      - Bear レジーム判定（ai_scores の regime_score 平均 < 0）を行い、Bear の場合は BUY を抑制
      - BUY 閾値はデフォルト 0.60。SELL（エグジット）ルールにストップロス（-8%）とスコア低下判定を実装
      - SELL を優先して BUY から除外、signals テーブルへ日付単位で置換して書き込む（トランザクションで保証）
- DB 操作の共通方針
  - DuckDB への INSERT は可能な箇所で冪等性を考慮（ON CONFLICT DO UPDATE / DO NOTHING）
  - 大量処理時にトランザクションとバルク挿入を用いることで原子性と性能を確保

Security
- 外部入力（RSS/XML）処理に defusedxml を使用して XML 関連の脆弱性を低減
- RSS URL 正規化とトラッキングパラメータ除去により重複登録の抑制
- J-Quants クライアントでタイムアウト・リトライ・レート制御を実装して API リソース悪用を抑制

Notes
- 多くの処理は DuckDB 接続を受け取り、prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals 等のテーブルを参照・更新します。テーブル定義（スキーマ）は別途用意する必要があります。
- ルックアヘッドバイアス防止の設計が散見されます（取得時の fetched_at、target_date 時点のデータのみ参照する方針など）。
- 一部モジュール（例: execution, monitoring）の詳細実装は今回のリリースでは最小限または空のエントリとなっています（将来の拡張対象）。

Acknowledgements / Future work
- トレーリングストップや時間決済など、完全なエグジットロジックの追加（positions テーブル拡張が必要）は今後の課題として記載されています。
- News → symbol マッチングや記事の NLP 処理、AI スコア算出ロジックは外部モジュール/実装に依存する想定で、今後実装予定。

---

（この CHANGELOG はリポジトリ内のコード内容から推測して作成しています。実際の変更履歴や設計文書に基づく差分とは異なる場合があります。）