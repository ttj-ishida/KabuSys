# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

（現時点のコードベースに未リリースの変更はありません）

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム "KabuSys" のコア機能を実装しました。以下はコードベースから推測される主要な追加点・設計方針・既知の制約です。

### 追加 (Added)
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0。
  - 公開モジュール: data, strategy, execution, monitoring（execution は空のパッケージ初期化ファイルを含む）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により実行カレントディレクトリに依存しない読み込みを実現。
  - .env のパースはコメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境（development, paper_trading, live）/ログレベル等の取得を型付けして提供。未設定の必須環境変数は ValueError で通知。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装（トークン取得、ページネーション対応の取得関数、DuckDB への保存関数）。
  - RateLimiter（120 req/min 固定間隔スロットリング）を実装し API レート制限を保護。
  - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象にし、429 の場合は Retry-After を尊重。
  - 401 応答時はリフレッシュトークンで自動的に ID トークンを再取得して 1 回リトライ。
  - データ保存は冪等（ON CONFLICT DO UPDATE）で実装: raw_prices / raw_financials / market_calendar に対応。
  - 取得日時（fetched_at）を UTC ISO8601 で保存し、Look-ahead バイアス監査を可能に。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得・前処理して raw_news へ保存する仕組み（既定ソースに Yahoo Finance Business RSS を含む）。
  - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）・記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
  - defusedxml を用いて XML 攻撃対策、受信サイズ上限（10MB）設定、HTTP スキーム検証等のセキュリティ対策を実装。
  - DB へのバルク INSERT はチャンク化して実行し、INSERT RETURNING 相当の結果を元に実際に挿入された件数を返す設計（実装方針の説明が含まれる）。

- 研究（Research）モジュール (src/kabusys/research/)
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを計算。
    - 各関数は (date, code) キーの dict リストを返す設計で、Z スコア正規化ユーティリティ（kabusys.data.stats.zscore_normalize）と連携。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンランク相関（IC）を計算。サンプル不足や定数ベクトルを適切に扱う。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクとする安定したランク計算を実装（浮動小数丸めで ties 対策）。
  - research パッケージは zscore_normalize などを再エクスポート。

- 特徴量作成・正規化 (src/kabusys/strategy/feature_engineering.py)
  - 研究環境で算出された生ファクターを統合して features テーブルへ UPSERT（ターゲット日付で削除→挿入する日付単位置換、トランザクション使用）する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
  - 対象カラムを Z スコア正規化し ±3 でクリップ。正規化は kabusys.data.stats.zscore_normalize を使用。
  - トランザクションと例外時のロールバック処理を明示。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して final_score を算出し、BUY / SELL シグナルを生成して signals テーブルへ書き込む generate_signals を実装。
  - コンポーネントスコア: momentum / value / volatility / liquidity / news。news は AI スコアから取得し、未登録は中立で補完。
  - 重みのマージ・正規化ロジックを実装（デフォルト重みを提供、ユーザー重みは検証して合成、合計が 1 でない場合は再スケール）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負なら Bear。ただしサンプル数が閾値未満なら Bear としない）。
  - BUY は閾値（デフォルト 0.60）以上で生成。ただし Bear では BUY を抑制。
  - SELL はストップロス（-8%）とスコア低下（final_score < threshold）で判定。positions / prices を参照して判定する実装。
  - signals は日付単位で置換（トランザクション＋バルク挿入）して冪等性を確保。

- DB / 型変換ユーティリティ
  - jquants_client において _to_float / _to_int を実装し、安全な数値変換を提供（不正フォーマットは None）。
  - 各種保存関数は PK 欠損行をスキップして警告ログを出す。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector で defusedxml を使用し XML 攻撃を軽減。
- RSS 取得時の受信サイズ上限・HTTP スキーム検証・トラッキングパラメータ除去などを実装し、SSR F / DoS リスクを低減する設計が盛り込まれている。

### 既知の制約・今後の改善メモ (Known issues / TODO)
- signal_generator のエグジット条件の一部（トレーリングストップ・時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。コメントで未実装箇所が明記されています。
- news_collector の詳細な記事→銘柄マッチング（news_symbols への紐付け）ロジックは設計方針に示されているものの、ソースマッチングの実装詳細はファイル内のコメントレベルに留まる可能性があります（コードの続きが存在する想定）。
- 柔軟なレート制御や分散環境での共有レート制限には追加設計が必要（現状はプロセス内固定スロットリング）。
- 一部ユーティリティ（例: kabusys.data.stats.zscore_normalize）の実装は別ファイルにあり、本リリースではそれと連携する形で利用されている。

もし CHANGELOG の粒度（追加で「機能別のセクションを増やす」「リリース日を変更する」等）を変更したい場合は指示ください。