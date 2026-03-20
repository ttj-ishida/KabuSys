# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]


## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム "KabuSys" のコア機能を提供します。以下の主要コンポーネントと公開 API を含みます。

### Added
- パッケージ基礎
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。
  - パッケージの公開 API（__all__）に data, strategy, execution, monitoring を追加。

- 環境設定 / ロード（kabusys.config）
  - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - .env パーサを実装（コメント/export/クォート/エスケープの取り扱い、インラインコメントルール）。
  - 環境変数読み取り用の Settings クラスを提供（必須キー取得時は例外を投げる）。
    - J-Quants / kabuステーション / Slack / DB パス / 実行環境判定（development/paper_trading/live）/ログレベル検証 等をサポート。
    - DB パスはデフォルトで data/kabusys.duckdb / data/monitoring.db。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装。
    - レート制限（120 req/min）を Respect する固定間隔レートリミッタを搭載。
    - リトライ（指数バックオフ、最大 3 回）と 401 時のトークン自動リフレッシュを実装。
    - ページネーション対応（pagination_key の取り扱い）。
    - Look-ahead Bias 対策としてフェッチ時刻を UTC（fetched_at）で記録。
  - DuckDB への冪等保存ユーティリティを提供:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
    - データ変換ユーティリティ `_to_float` / `_to_int` を実装。PK 欠損行はスキップして警告ログ。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存するモジュールを追加。
    - デフォルト RSS ソース（Yahoo Finance）を用意。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）を実装。
    - defusedxml を用いた XML パースによる安全処理、受信サイズ上限（10MB）による DoS 対策、SSRF 回避の注意喚起等の安全設計。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を用いることで冪等性を担保。
    - バルク INSERT のチャンク処理によるパフォーマンス対策。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算モジュール群を実装（prices_daily / raw_financials を参照）。
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日 MA）を計算。
    - calc_volatility: 20 日 ATR、atr_pct、avg_turnover、volume_ratio を計算（True Range の NULL 伝播を制御）。
    - calc_value: target_date 以前の最新財務データと結合して PER / ROE を計算。
  - 特徴量探索ユーティリティを提供:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括で取得。
    - calc_ic: スピアマン（ランク）による Information Coefficient の計算（有効サンプル 3 未満は None）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクとするランク付け（丸め処理で ties の検出を安定化）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールで計算した生ファクターを結合・正規化して features テーブルに保存する処理を実装（build_features）。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 正規化は zscore_normalize を使用し、対象カラムを ±3 でクリップ（外れ値対策）。
    - 日付単位の置換（DELETE + INSERT）をトランザクションで行い冪等性・原子性を確保。
    - prices_daily から target_date 以前の最新価格を参照してフィルタ処理を行うことで休場日欠損に対応。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出し、BUY / SELL シグナルを生成する処理を実装（generate_signals）。
    - デフォルト重み: momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10（重みはユーザ指定で上書き可能、合計は再スケール）。
    - BUY 閾値デフォルト 0.60（_DEFAULT_THRESHOLD）。
    - スコア計算の詳細:
      - モメンタム: momentum_20/momentum_60/ma200_dev をシグモイド変換して平均化。
      - バリュー: PER を 1/(1+PER/20) で変換（PER が無効なら None）。
      - ボラティリティ: atr_pct の Z スコアを反転してシグモイド変換。
      - 流動性: volume_ratio をシグモイド変換。
      - AI ニューススコアはシグモイド変換、未登録時は中立（0.5）。
      - 欠損コンポーネントは中立 0.5 で補完して不当な降格を防止。
    - Bear レジーム判定: ai_scores の regime_score の平均が負なら Bear（サンプル数が最小数未満なら判定しない）。Bear 時は BUY シグナルを抑制。
    - SELL（エグジット）判定:
      - ストップロス: 終値 / avg_price - 1 < -8%（優先処理）。
      - スコア低下: final_score が threshold 未満。
      - positions テーブルの価格欠損時は警告を出して SELL 判定をスキップ。
      - 未実装のエグジット条件（トレーリングストップ / 時間決済）はコメントで明示。
    - signals テーブルへの書き込みは日付単位の置換をトランザクションで行い冪等性を保証。
    - 生成結果は BUY と SELL の合計件数を返す。

- 低レベルユーティリティ
  - zscore_normalize（kabusys.data.stats 経由で利用）を用いた正規化設計を参照（実装は別モジュール）。
  - 各モジュールで詳細なログ出力（info/warning/debug）を実装し、異常時の挙動をトレース可能に。

### Security
- news_collector で defusedxml を使った XML パース、受信サイズ制限、URL 正規化、SSRF への配慮を行いセキュリティに配慮。
- .env ローダーは OS 環境変数を保護するため protected キー群を導入し、上書きルールを明確化。

### Notes / Design decisions
- DuckDB をデータ層（prices_daily / raw_financials / features / ai_scores / positions / raw_* テーブル群）に採用し、SQL と Python を組み合わせた処理を基本設計としています。
- ルックアヘッドバイアスを防ぐため、すべての集計・シグナル生成処理は target_date 時点の「当時アクセス可能なデータのみ」を前提とした実装になっています。
- 外部ライブラリ依存を最小化し、研究用途のモジュールでは pandas 等に依存しない設計としています（ただし defusedxml は XML 安全性のため採用）。
- 一部の挙動（例: トレーリングストップや時間決済）は将来的な実装項目としてコメントで残しています。

---

もし CHANGELOG に追加してほしい点（例えばリリースノートの粒度をさらに細かくする、各関数の変更履歴を別途分ける等）があれば指示してください。