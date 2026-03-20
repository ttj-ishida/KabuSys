# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の書式に準拠しています。  

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20
初期リリース。このバージョンで追加された主な機能・改善点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__）。バージョン番号を `__version__ = "0.1.0"` として定義。
  - モジュール公開 API を明示（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を追加。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に自動検出（CWD に依存しない）。
  - `.env`, `.env.local` の優先順位で読み込み。OS 環境変数の上書き保護機構を実装。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを無効化可能（テスト向け）。
  - `.env` パーサを実装:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - 行末コメント処理（クォート外での `#` の扱い）
  - Settings クラスを追加し、主要な設定値をプロパティ化:
    - J-Quants / kabu ステーション / Slack / DB パス等
    - `env`（development/paper_trading/live）と `log_level` の検証（無効値は ValueError）

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装:
    - 固定間隔のレートリミッタ（120 req/min 相当）
    - リトライ（指数バックオフ、最大 3 回）と特定ステータス（408/429/5xx）での再試行
    - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回まで）
    - ページネーション対応の fetch 関数:
      - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - DuckDB への保存用ユーティリティ（冪等性を考慮して ON CONFLICT DO UPDATE を使用）:
      - save_daily_quotes / save_financial_statements / save_market_calendar
    - 型変換ユーティリティ `_to_float`, `_to_int` を実装（安全な変換ロジック）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集モジュールを実装（デフォルトは Yahoo Finance ビジネスカテゴリ RSS）。
  - セキュリティと堅牢性を考慮:
    - defusedxml を用いて XML 関連攻撃対策
    - 受信サイズ上限（10 MB）でメモリ DoS を防止
    - URL 正規化（トラッキングパラメータ除去、キーでソート、フラグメント削除）
    - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成して冪等性を担保
    - HTTP/HTTPS 以外のスキームを拒否する等の SSRF 緩和措置（実装方針に反映）
  - DB へのバルク挿入のチャンク処理（チャンクサイズ）とトランザクション最適化

- 研究用ファクター計算（kabusys.research.*）
  - ファクター計算モジュール群を追加:
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）
      - calc_volatility: 20 日 ATR（atr_20 / atr_pct）、平均売買代金、volume_ratio
      - calc_value: PER / ROE（raw_financials と prices_daily を参照）
    - feature_exploration:
      - calc_forward_returns: 複数ホライズン（デフォルト 1,5,21 営業日）での将来リターン一括取得（単一クエリ）
      - calc_ic: スピアマンのランク相関（Information Coefficient）計算
      - factor_summary: 基本統計量（count, mean, std, min, max, median）
      - rank: 同順位は平均ランクとするランク関数（ランク算出の丸め処理あり）
  - 研究用 API は DuckDB の prices_daily / raw_financials テーブルのみを参照し、本番 API へは依存しない設計

- 戦略（kabusys.strategy.*）
  - feature_engineering.build_features:
    - research モジュールから生ファクターを取得し、ユニバースフィルタ（最低株価・平均売買代金）を適用
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）と ±3 クリップ
    - 日付単位の置換（DELETE + バルク INSERT）で冪等性と原子性を確保（トランザクション）
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネント・スコア（momentum/value/volatility/liquidity/news）を計算
    - デフォルト重みとしきい値（DEFAULT_WEIGHTS / DEFAULT_THRESHOLD）を備え、ユーザ指定重みは検証・リスケールされる
    - AI レジームスコアにより Bear 判定を行い、Bear では BUY を抑制
    - SELL（エグジット）判定を実装（ストップロス、スコア低下）
    - BUY/SELL を signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）
    - 欠損コンポーネントは中立値（0.5）に補完して過度な降格を防止

### Changed
- （初回リリースのため該当なし）

### Fixed / Reliability improvements
- env パーサの細かな取り扱いを実装（エスケープ、インラインコメント、export キーワード対応）し、.env のパース堅牢性を改善。
- DuckDB への保存処理で PK 欠損行はスキップしログ出力するようにして不整合データに対処。
- API 呼び出しでのリトライ/バックオフ・トークンリフレッシュ処理により外部依存の堅牢性を向上。

### Security
- news_collector で defusedxml を利用して XML の脆弱性対策を実施。
- ニュース URL の正規化とトラッキングパラメータ除去、HTTP スキーム制限等で SSRF / トラッキング対策を実装。
- 資格情報の取得は環境変数経由（Settings）とし、必須未設定時は ValueError を投げることで明確に失敗する設計。

### Performance
- DuckDB 上でウィンドウ関数を活用した一括集計によりファクター計算や将来リターン計算を高速化。
- J-Quants クライアントは固定間隔スロットリングを実装し、レート制限に従った安定したデータ取り込みを実現。
- raw_news のバルク挿入はチャンク処理で SQL 長やパラメータ数の制限に配慮。

### Notes / Operational
- Settings.env と LOG_LEVEL は許容値以外は ValueError を送出するため、CI/デプロイ時に環境変数の検証が容易。
- データ取り込み・ファクター/シグナル生成の各処理は「target_date」時点のデータのみを参照する設計で、ルックアヘッドバイアスを防止。
- 自動 .env 読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD

---
今後のリリースでは以下を検討しています（未実装／TODO の一例）:
- signal_generator の追加エグジット条件（トレーリングストップ、時間決済）の実装（positions テーブルの拡張が必要）。
- ニュースと銘柄のマッピング強化（ニュース中のシンボル抽出・マッチング精度向上）。
- monitoring / execution 層の具体実装（発注 API 連携、実行ログ・メトリクス収集）。

以上。