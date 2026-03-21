# CHANGELOG

すべての重要な変更は Keep a Changelog の仕様に従って記載します。  
このプロジェクトはセマンティック バージョニングに従います。

## [0.1.0] - 2026-03-21

初回リリース。

### Added
- パッケージ初期化
  - パッケージバージョンを定義: `kabusys.__version__ = "0.1.0"`。
  - public API を制御する `__all__` を設定（data, strategy, execution, monitoring）。

- 環境設定管理 (`kabusys.config`)
  - `.env` / `.env.local` ファイルや OS 環境変数からの設定自動読み込みを実装（プロジェクトルートは `.git` または `pyproject.toml` で探索）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーを実装:
    - 空行 / コメント行の無視、`export KEY=val` 形式の対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ対応。
    - クォート無し値のインラインコメント扱い（直前が空白/タブの場合）。
  - 環境変数保護機能（OS 環境変数を上書きしない / `.env.local` による上書きは保護除外）を実装。
  - 必須環境変数を取得する `_require`、Settings クラスを提供（J-Quants / kabu ステーション / Slack / DB パス / 環境判定 / ログレベル等のプロパティ）。
  - `KABUSYS_ENV` と `LOG_LEVEL` の許容値チェックを実装。

- データ取得・保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - API クライアントを実装（`_request`, `get_id_token`, `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`）。
  - レート制限ガード（固定間隔スロットリング、デフォルト 120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 受信時にリフレッシュトークンで自動再取得して 1 回リトライする仕組みを実装（トークンキャッシュ共有）。
  - ページネーション対応（pagination_key の処理）。
  - DuckDB へ冪等に保存するユーティリティ（`save_daily_quotes`, `save_financial_statements`, `save_market_calendar`）を実装。いずれも ON CONFLICT（重複時更新）を利用。
  - レスポンス値を安全に変換する `_to_float`, `_to_int` ユーティリティ。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードから記事を収集して `raw_news`（および関連テーブル）へ冪等保存する基本実装を追加。
  - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント削除、クエリパラメータキーソート）を実装。
  - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保する方針を採用。
  - defusedxml による XML パースで XML Bomb 等の脆弱性を緩和。
  - HTTP(S) 限定、受信最大バイト数（10MB）制限、SSRF やメモリ DoS を考慮した実装設計。
  - バルク INSERT チャンク処理を導入して DB 書き込みのオーバーヘッドを抑制。

- リサーチ / ファクター計算群 (`kabusys.research`)
  - ファクター計算モジュール（`factor_research.py`）を提供:
    - モメンタム（mom_1m / mom_3m / mom_6m / ma200_dev）
    - ボラティリティ・流動性（atr_20 / atr_pct / avg_turnover / volume_ratio）
    - バリュー（per / roe、raw_financials から最新財務を結合）
    - 各関数は DuckDB の `prices_daily` / `raw_financials` のみ参照し、(date, code) ベースで dict リストを返す設計。
  - 研究用ユーティリティ（`feature_exploration.py`）を実装:
    - 将来リターン計算 `calc_forward_returns`（複数ホライズン対応、ホライズン上限バリデーション）。
    - スピアマン IC 計算 `calc_ic`（ランク相関、欠損・最小サンプル制限あり）。
    - ランク変換 `rank`（同順位は平均ランク、丸めによる ties 検出対策あり）。
    - 統計サマリー `factor_summary`（count/mean/std/min/max/median を計算）。
  - 研究用モジュール群をパッケージエクスポートに追加。

- 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
  - 研究環境で計算した生ファクターを取り込み、正規化・合成して `features` テーブルへ UPSERT（日付単位の置換）する `build_features` を実装。
  - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を実装。
  - Z スコア正規化（`kabusys.data.stats.zscore_normalize` を利用）、±3 でクリップして外れ値を抑制。
  - トランザクション + バルク挿入で日次の置換を原子性で保証。

- シグナル生成 (`kabusys.strategy.signal_generator`)
  - 正規化済み features と ai_scores を統合して各銘柄の final_score を計算し、BUY/SELL シグナルを生成して `signals` テーブルへ書き込む `generate_signals` を実装。
  - 統合スコアのデフォルト重みと閾値を実装:
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
    - デフォルト閾値: 0.60
  - コンポーネントスコア算出:
    - モメンタムはシグモイド変換後の平均、
    - バリューは PER を 20 を基準に変換、
    - ボラティリティは atr_pct の反転シグモイド、
    - 流動性は volume_ratio のシグモイド。
  - AI レジームスコア集計により Bear レジームを判定し、Bear 時は BUY シグナルを抑制。
  - エグジット判定（STOP LOSS: -8% 以下、スコア低下）を実装。トレーリングストップ・時間決済は未実装（要追加データ）。
  - weights 引数の検証とスケーリング（未知キーや無効値は無視、合計が 1.0 になるよう再スケール）。
  - SELL を優先して BUY から除外するポリシー、日付単位の置換はトランザクションで行い原子性を保証。

### Security
- ニュース収集で defusedxml を使用して XML 攻撃を緩和。
- RSS / URL 正規化でトラッキングパラメータを削除、HTTP(S) 以外のスキーム拒否など SSRF 対策方針を明示。
- J-Quants クライアントでタイムアウト設定と堅牢なエラーハンドリングを実装。

### Reliability / Robustness
- API クライアントにレートリミッタ・再試行・トークン自動更新を実装し、外部依存処理の信頼性を向上。
- DB 操作でトランザクション（BEGIN/COMMIT/ROLLBACK）を明示的に利用して原子性・冪等性を確保。
- 入力値検証（horizons, weights, env 値など）やログ出力で異常系の可観測性を向上。

### Performance
- DuckDB へのバルク挿入（executemany）を多用、news_collector ではチャンク処理を導入して SQL パラメータ数制限を回避。
- jquants_client のページネーション対応によりネットワーク転送の最小化を想定。

### Notes / Known limitations
- execution / monitoring パッケージはインターフェースレベルのみで、実行層（発注 API 結合など）は本リリースでは依存を持たない設計。
- signal_generator の一部のエグジット条件（トレーリングストップ、時間決済）は positions テーブルに追加情報（peak_price / entry_date 等）が必要であり未実装。
- 一部の計算（例: factor normalizer の実装は別モジュール `kabusys.data.stats` に依存）とテーブル定義は本リリースに含まれる想定だが、別途 DB スキーマの準備が必要。

---

今後のリリースでは、以下を優先的に改善予定です:
- execution 層の実装（kabu ステーション連携、注文発行ロジック）。
- モニタリングとアラート機能の充実（Slack 通知・監視）。
- news_collector の銘柄紐付け（正規表現マッチ / NER 等）と挙動改善。
- より詳細なテストと CI の整備。