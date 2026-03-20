Keep a Changelog 準拠 — 変更履歴
=================================

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に従っています。
リリース日付はパッケージの __version__ と現行日付に基づき記載しています。

[0.1.0] - 2026-03-20
--------------------

### Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パブリック API をエクスポート:
    - kabusys.__all__: data, strategy, execution, monitoring
  - バージョン情報: kabusys.__version__ = "0.1.0"

- 設定/環境管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む自動ローダーを追加
    - プロジェクトルート判定: .git または pyproject.toml を探索してルートを自動検出
    - 読み込み優先順: OS 環境変数 > .env.local > .env
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - 高度な .env パーサー実装:
    - コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント対応
    - 無効行や PK 欠損を安全にスキップ
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル等のプロパティ
    - env / log_level の妥当性チェック（許容値セットで検証）
    - is_live / is_paper / is_dev の便利プロパティ

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装 (RateLimiter)
    - 冪等的な DuckDB への保存関数:
      - save_daily_quotes, save_financial_statements, save_market_calendar
      - ON CONFLICT DO UPDATE による upsert で重複を排除
    - ページネーション対応 fetch_* 関数（daily_quotes / statements / trading_calendar）
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）
    - 401 応答時の自動トークンリフレッシュ（1 回のみ）を実装
    - id_token キャッシュをモジュールレベルで保持（ページネーション間で共有）
    - データ変換ユーティリティ (_to_float / _to_int) を追加

- ニュース収集（kabusys.data.news_collector）
  - RSS から記事を取得して raw_news に保存するパイプラインを実装
    - URL 正規化（トラッキングパラメータ除去、クエリ整列、フラグメント除去）
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保
    - defusedxml による XML パースで XML Bomb 等に対する防御
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、HTTP スキーム制限などによる SSRF / DoS 緩和策
    - bulk insert チャンク実装で DB 負荷を抑制

- 研究用ファクター計算（kabusys.research）
  - factor_research モジュールを実装:
    - calc_momentum: 1m/3m/6m リターン、MA200 乖離率の計算
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率
    - calc_value: 財務データ（EPS/ROE）と価格から PER/ROE を算出（最新財務レコードを参照）
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得
    - calc_ic: ランク相関 (Spearman ρ) による IC 計算
    - factor_summary: count/mean/std/min/max/median の統計サマリー
    - rank: 平均ランク（同順位は平均ランク）
  - 研究用 API を re-export（kabusys.research.__all__）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装:
    - research の calc_* 関数から得た raw factor をマージ
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用
    - 数値ファクターを Z スコア正規化（kabusys.data.stats:zscore_normalize を利用）し ±3 でクリップ
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT をトランザクションで実行）し冪等性を保証

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold, weights) を実装:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news の各コンポーネントスコアを算出
    - コンポーネント毎にシグモイド変換や反転処理を適用
    - デフォルト重みを用いた最終スコア final_score を計算、閾値を超える銘柄を BUY と判定
    - Bear レジーム（ai_scores の regime_score 平均 < 0、十分なサンプル数がある場合）では BUY を抑制
    - SELL（エグジット）判定を実装:
      - ストップロス（終値/avg_price - 1 < -8%）
      - final_score が閾値未満
    - SELL を優先して BUY から除外、signals テーブルへ日付単位の置換で保存（冪等）
    - weights の検証と合成・再スケール処理（未知キーや無効値を除外）

- パッケージ構成
  - strategy パッケージで build_features / generate_signals を公開
  - research, data モジュール群を整備
  - execution パッケージは初期スタブを配置（将来のエグゼキューション層実装のためのプレースホルダ）

### Changed
- N/A（初期リリースのため既存機能の変更なし）

### Fixed
- N/A（初期リリース）

### Security
- news_collector で defusedxml を利用し XML 脆弱性を軽減
- news_collector で受信サイズ上限・URL スキーム検査等を実装し SSRF / メモリ DoS を低減
- jquants_client の HTTP リトライ時に 429 の Retry-After を尊重する実装（負荷軽減）

### Notes / Design decisions
- DuckDB への書き込みは基本的にトランザクション（BEGIN/COMMIT/ROLLBACK）とバルク挿入で原子性・効率を重視
- look-ahead bias を避けるため、すべての戦略 / 研究関数は target_date 時点までのデータのみ参照する設計
- ai_scores が存在しない場合はニューススコアを中立で補完する仕組みを採用（欠損銘柄の不当な降格を防止）
- デフォルトの重み集合は StrategyModel.md に基づくが、ユーザー指定の weights を受け付け、妥当性検証後に再スケールする

### Known limitations / TODOs
- signal_generator の SELL 判定について、ドキュメントにある以下の条件は未実装（後続リリースで対応予定）:
  - トレーリングストップ（peak_price / entry_date が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- execution 層（発注・約定処理）は現時点で未実装（パッケージ内にスタブのみ）
- monitoring モジュールはコードベースに名前は含まれるが、実装が未導入

開発・運用に関する問い合わせはリポジトリの issue にてお願いします。