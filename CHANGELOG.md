# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
慣例に従いセマンティックバージョニングを使用します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点は以下の通りです。

### 追加（Added）
- パッケージ基礎
  - パッケージルート `kabusys` を追加。バージョンは `0.1.0`。
  - パブリック API: `kabusys.data`, `kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring` を公開。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイル（`.env` と `.env.local`）および環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートは `.git` または `pyproject.toml` を基準に検出）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - .env の行パーサを実装（`export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメント、トラッキング）。
  - Settings クラスを実装してアプリケーション設定を型付きプロパティで提供（J-Quants トークン、kabuAPI パスワード、Slack トークン/チャンネル、DB パス、環境/ログレベルなど）。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値チェック）を実装。

- データ収集 / 永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔（120 req/min）を守るレートリミッタを導入。
    - リトライ（指数バックオフ、最大 3 回）および 408/429/5xx に対する再試行ロジック実装。
    - 401 Unauthorized 受信時にリフレッシュトークンから ID トークンを再取得して再試行する自動リフレッシュ機能（1 回のみ）。
    - ページネーション対応の取得（`pagination_key` を利用）。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し、ルックアヘッドバイアスのトレーサビリティを確保。
  - DuckDB への保存関数を実装（冪等性を保つため ON CONFLICT DO UPDATE を利用）:
    - 株価日足: `save_daily_quotes`
    - 財務データ: `save_financial_statements`
    - 市場カレンダー: `save_market_calendar`
  - データ変換ユーティリティ（安全な float/int 変換）を実装。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集モジュールを実装（デフォルトソースとして Yahoo Finance を追加）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）を実装。
  - defusedxml を使った安全な XML パース、受信サイズ上限（10 MB）、SSRF/不正スキーム対策等を考慮した設計。
  - 記事IDは正規化URLの SHA-256 を利用して冪等性を担保。
  - DB へのバルク挿入でチャンク処理を行う実装。

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日MA乖離）を計算する `calc_momentum` を実装。
    - Volatility: 20日ATR/相対ATR、20日平均売買代金、出来高比率を計算する `calc_volatility` を実装。
    - Value: 財務情報（EPS/ROE）と株価から PER/ROE を組み合わせて計算する `calc_value` を実装。
    - 各関数は DuckDB の `prices_daily` / `raw_financials` テーブルのみを参照する設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン）`calc_forward_returns` を実装。単一クエリで複数ホライズン取得。
    - IC（スピアマンランク相関）計算 `calc_ic`、ランク変換ユーティリティ `rank` を実装（同順位は平均ランク）。
    - ファクター列の統計サマリーを返す `factor_summary` を実装（count/mean/std/min/max/median）。

- 戦略（strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - 研究環境で計算された生ファクターをマージ、ユニバースフィルタ（最低株価/平均売買代金）を適用し、Z スコア正規化（指定カラム）・±3クリップして `features` テーブルに UPSERT する `build_features` を実装。
    - DuckDB トランザクションを使った日付単位の置換（冪等）を実装。
  - シグナル生成（kabusys.strategy.signal_generator）
    - `features` と `ai_scores` を統合、モメンタム/バリュー/ボラティリティ/流動性/ニュースの各コンポーネントを算出し、重み付き合算による `final_score` を計算する `generate_signals` を実装。
    - デフォルト重みと閾値（デフォルト BUY 閾値 0.60）を実装。ユーザー指定の重みは検証・正規化してフォールバック。
    - Bear レジーム判定（AI の regime_score の平均が負の場合に BUY を抑制）。
    - エグジット（SELL）判定（ストップロス -8% / スコア低下）を実装（保有ポジションの最新情報に基づく）。
    - BUY/SELL を `signals` テーブルへ日付単位の置換で保存（冪等）。

### 改善（Changed）
- J-Quants クライアント
  - レートリミットを固定間隔スロットリングで実装し、ページネーション間でもトークンを再利用するためのモジュールレベルの ID トークンキャッシュを追加。
  - リトライ時に 429 の Retry-After ヘッダを優先して待機時間を決定。

- .env パーサ
  - シングル/ダブルクォート内のバックスラッシュエスケープやインラインコメントの取り扱いを改善。
  - export プレフィックスの扱いに対応。

- DB 保存処理
  - PK 欠損行をスキップして警告を出力するようにし、無効データによる例外発生を予防。

### 修正（Fixed）
- DuckDB への保存処理での不整合や無効レコードによる障害を回避するため、PK 欠損時に該当行をスキップするロジックを追加。
- HTTP/ネットワークエラー時のリトライ制御（バックオフ）を強化し、429/Retry-After の扱いを改良。

### セキュリティ（Security）
- RSS パースに defusedxml を使用し、XML エンティティ拡張攻撃等への対策を導入。
- ニュース収集において受信サイズ上限を設け、メモリ DoS を緩和。
- RSS の URL 正規化でトラッキングパラメータを除去し、また HTTP スキームのホワイトリスト的扱いを想定した実装方針を採用（SRRF 対策）。

### 既知の未実装 / 制限（Known issues / Limitations）
- signal_generator のトレーリングストップや時間決済（保有 60 営業日超）など一部エグジット条件は未実装（positions テーブルに peak_price / entry_date が必要）。
- research モジュールは外部依存（pandas 等）を避け標準ライブラリと DuckDB SQL で実装しているため、非常に大規模データでの最適化は今後の課題。
- `kabusys.execution` と `kabusys.monitoring` パッケージのエントリは公開されているが、実装はこれから。

---

今後の予定（例）
- execution 層の発注ラッパ実装（kabuステーション API 連携）
- monitoring（監視・アラート）、Slack 通知統合の実装・強化
- テストカバレッジ拡充、CI パイプライン整備

（以上）