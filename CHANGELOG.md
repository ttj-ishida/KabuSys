# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-21

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ名と __version__ を設定。
  - パッケージ外部 API を公開: data, strategy, execution, monitoring（execution はモジュールのスケルトンを含む）。
- 環境変数 / 設定管理（kabusys.config）
  - .env/.env.local をプロジェクトルートから自動読み込み（.git または pyproject.toml を基準にプロジェクトルートを特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env パーサー実装: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを考慮。
  - ロード時の既存 OS 環境変数保護（protected set）および .env.local による上書き処理。
  - Settings クラスを提供し、必須環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_* 等）や DB パス、環境（development/paper_trading/live）・ログレベルの検証を行うプロパティを実装。
- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（株価日足 / 財務データ / マーケットカレンダーの取得）。
  - ページネーション対応とモジュールレベルの ID トークンキャッシュを実装（ページ間でトークン共有）。
  - レートリミッタ実装（固定間隔スロットリングで 120 req/min 制限を遵守）。
  - 再試行（リトライ）ロジックを備えた HTTP 呼び出しを実装（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。429 の場合は Retry-After ヘッダを考慮。
  - 401 Unauthorized 受信時は自動でリフレッシュトークンから ID トークンを再取得して 1 回リトライする処理を実装（無限再帰を防止）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE を使用して冪等性を確保、PK 欠損行のスキップとログ出力対応。
  - レスポンスの JSON デコード失敗時に詳細情報を含めてエラー報告。
  - 型変換ユーティリティ（_to_float / _to_int）を追加し、不正値や空文字への寛容な扱いを実装。
- ニュース収集ユーティリティ（kabusys.data.news_collector）
  - RSS フィード収集のためのユーティリティを追加（RSS ソース定義、最大受信バイト数制限、URL 正規化ユーティリティなど）。
  - URL 正規化: スキーム/ホストの小文字化、トラッキングパラメータ（utm_* 等）の削除、フラグメント削除、クエリパラメータのソートを実装。
  - defusedxml を用いた安全な XML パースや、受信サイズ制限等のメモリ保護方針を明示。
  - 大量挿入のためのチャンク処理定数を用意（INSERT チャンクサイズ制限）。
- 研究用モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（約1/3/6ヶ月リターン、MA200 乖離率）
    - ボラティリティ / 流動性（20日 ATR、ATR 比率、20日平均売買代金、出来高比率）
    - バリュー（PER、ROE） — raw_financials からの最新財務データ結合に対応
    - DuckDB を用いた SQL ベースの効率的な実装（スキャン範囲のバッファ等の最適化）
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：複数ホライズン対応、1 クエリでまとめて取得
    - IC（Information Coefficient）計算（calc_ic）：スピアマンランク相関（ランク化ユーティリティ rank を含む）
    - factor_summary：各ファクター列の基本統計量（count/mean/std/min/max/median）計算
  - 研究用 API を re-export（calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）
- 戦略モジュール（kabusys.strategy）
  - 特徴量エンジニアリング（strategy.feature_engineering）
    - research で計算した生ファクターをマージしてユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用
    - 指定カラムの Z スコア正規化（zscore_normalize を利用）と ±3 クリップ処理を実装
    - DuckDB の features テーブルへ日付単位で置換（削除→挿入、トランザクションで原子性）する build_features を実装（冪等）
  - シグナル生成（strategy.signal_generator）
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - シグモイド変換、欠損値は中立 0.5 で補完、重みのバリデーションと正規化対応
    - Bear レジーム判定（ai_scores の regime_score の平均が負の場合）に基づく BUY 抑制
    - BUY 閾値（デフォルト 0.60）超過で BUY シグナルを生成、STOP-LOSS（-8%）やスコア低下で SELL シグナルを生成
    - positions / prices_daily を参照して保有ポジションのエグジット判定を行い、signals テーブルへ日付単位で置換する generate_signals を実装（冪等、トランザクションで原子性）
    - 重複・欠損に対する防御的実装（無効重みのスキップ、価格欠損時の SELL 判定スキップ、features にない保有銘柄は score=0 とみなす等）
- データ処理ユーティリティ
  - zscore_normalize（kabusys.data.stats）を想定した統合（research / strategy で使用）

Fixed / Improved
- DuckDB トランザクション制御の堅牢化
  - build_features/generate_signals 内での BEGIN/COMMIT/ROLLBACK を適切に扱い、ROLLBACK 失敗時には警告ログを出す設計。
- API 通信の信頼性向上
  - ネットワーク・HTTP エラーに対するリトライと指数バックオフ、429 の Retry-After 優先などを導入。
- データ整合性保護
  - save_* 系で PK 欠損行をスキップして警告ログを出す挙動を追加し、不正なデータによる DB 破壊を防止。

Security
- ニュースパーサで defusedxml を使用して XML インジェクション系の攻撃（XML Bomb 等）を軽減。
- ニュース URL 正規化でトラッキングパラメータを除去し、記事 ID を一意ハッシュで生成する方針を明示（冪等性向上）。
- RSS 受信サイズ上限（10 MB）を設定し、メモリ DoS を軽減。

Notes / Known limitations
- execution パッケージは空の初期スケルトン（実際の発注ロジックは未実装）。
- ニュース収集モジュールはセキュリティや正規化ユーティリティを提供するが、記事と銘柄の紐付け（news_symbols への登録など）の完全なワークフローは別実装が必要。
- 一部アルゴリズム（例: トレーリングストップ、時間決済）は設計書で言及されているが、現バージョンでは未実装（signal_generator 内に TODO 記載）。
- 外部依存を最小化する方針のため、研究モジュールは pandas 等に依存せず標準ライブラリ＋DuckDB SQL で実装されている。大規模データでのパフォーマンスは運用時に検証が必要。

---

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートはリリースプロセスに基づき適宜更新してください。）