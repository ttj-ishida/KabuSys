# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠して記載しています。  
このファイルはコードベースから推測して作成した初期リリース向けの変更履歴です。

全般的な注記
- 本リリースはパッケージバージョン 0.1.0（src/kabusys/__init__.py の __version__ に基づく）を想定した初回公開相当の内容です。
- DuckDB をデータ処理の中心に据えた設計、J-Quants API・RSS ニュース収集・研究用ファクター計算・戦略シグナル生成等の機能群を含みます。
- 本CHANGELOGはコードから挙動・設計方針を推測して要約しています。

[0.1.0] - 2026-03-21
----------------------------------------

Added
- 基本パッケージ構成を追加
  - モジュール: kabusys (data, strategy, execution, monitoring を __all__ で公開)
- 環境設定管理（kabusys.config）
  - .env ファイルおよび OS 環境変数からの自動ロード機能を実装
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能
  - 高度な .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ対応）
  - Settings クラスを提供し、J-Quants トークン、kabu API 関連、Slack、DB パス、環境種別・ログレベルなどのアクセスをプロパティで取得
  - 環境値の妥当性チェック（KABUSYS_ENV の許容値、LOG_LEVEL の許容値など）
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装
    - 固定間隔のレートリミッタ（120 req/min）を実装
    - リトライロジック（指数バックオフ、最大 3 回、特定ステータスコードでのリトライ）
    - 401 発生時の自動トークンリフレッシュ（1 回）対応
    - ページネーション対応でのデータ取得ロジック
    - JSON デコードエラー時に明確な例外メッセージ
  - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を追加（ページネーション対応）
  - DuckDB への保存関数を追加（冪等性を意識）
    - save_daily_quotes: raw_prices テーブルへの保存（ON CONFLICT ... DO UPDATE）
    - save_financial_statements: raw_financials テーブルへの保存（ON CONFLICT ... DO UPDATE）
    - save_market_calendar: market_calendar テーブルへの保存（ON CONFLICT ... DO UPDATE）
  - 型変換ユーティリティ: _to_float / _to_int を実装し安全にパース
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集・正規化して raw_news に保存する機能を追加
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等への防御）
    - HTTP/HTTPS スキーム以外の拒否、受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）
    - トラッキングパラメータ（utm_*, fbclid 等）の除去と URL 正規化
    - 記事 ID は URL 正規化後の SHA-256 の先頭 32 文字を使用して冪等性を確保
  - バルク INSERT のチャンク処理、挿入済み件数の正確な把握を行う設計
  - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を設定
- 研究用ファクター計算（kabusys.research）
  - factor_research モジュールを実装
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（ウィンドウの不足時は None）
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、avg_turnover、volume_ratio を計算
    - calc_value: EPS/ROE を raw_financials と prices_daily から組合せて PER/ROE を計算（EPS が 0/欠損なら None）
    - DuckDB のウィンドウ関数を活用した効率的な実装
  - feature_exploration モジュールを実装
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得
    - calc_ic: Spearman の順位相関（Information Coefficient）を実装（同位は平均ランク）
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算
    - rank: 同順位は平均ランクとする実装（丸めによる ties の検出対策あり）
  - research パッケージの __init__ で主要関数を再エクスポート
  - 外部ライブラリ（pandas 等）に依存しない純粋 Python + DuckDB の実装方針
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features を実装
    - research 側で計算した生ファクター（momentum/volatility/value）をマージ、ユニバースフィルタ適用、Zスコア正規化、±3 でクリップして features テーブルに UPSERT（日付単位で置換）するワークフロー
    - ユニバースフィルタ: 最低株価 300 円、20 日平均売買代金 5 億円
    - 正規化対象カラムの指定とクリップ処理、原子性を考慮したトランザクション処理
- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals を実装
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付き合算で final_score を算出
    - デフォルト重みと閾値（default threshold = 0.60）を実装し、ユーザ指定 weights を検証・補完・正規化する処理を追加
    - シグモイド変換や欠損コンポーネントの中立補完（0.5）を導入して堅牢性を確保
    - Bear レジーム検知（ai_scores の regime_score を平均し負なら Bear、サンプル数閾値あり）で BUY シグナルを抑制
    - SELL シグナル（エグジット）はストップロス（終値が avg_price に対して -8% 以下）とスコア低下を実装（トレーリングストップ等は未実装）
    - signals テーブルへ日付単位の置換（原子性を確保）
- 戦略パッケージの公開インターフェース（kabusys.strategy.__init__）で build_features / generate_signals を公開
- ロギングや警告メッセージの充実
  - 例: DB 保存時の PK 欠損スキップ、price 取得失敗による SELL 判定スキップ、weights の無効値ログなど

Changed
- 初回リリースにつき "Changed" の履歴はありません（初版追加項目のみ）。

Fixed
- 初回リリースにつき "Fixed" の履歴はありません。

Deprecated
- なし

Removed
- なし

Security
- ニュース収集で defusedxml を採用し XML の脆弱性に対処
- RSS パース・URL 正規化時にトラッキングパラメータの除去、受信サイズ制限、スキーム検査等を実装し SSRF / DoS /情報漏洩リスクを軽減
- J-Quants クライアントでタイムアウト・リトライ・トークンリフレッシュを実装し異常時の安全な復旧を考慮

移行 / 利用上の注意（推測）
- .env 自動ロードはパッケージ導入後もプロジェクトルートを検出して働きますが、テスト時等に自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants 用の refresh token 等の必須環境変数が不足していると Settings のプロパティアクセスで ValueError が発生します。.env.example を参照して .env を整備してください。
- DuckDB のスキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）が前提です。利用前に必要なテーブル定義を準備してください。
- 一部の戦略ロジック（例: トレーリングストップ、保有期間での強制クローズ等）は未実装で、将来的な拡張に備えた設計になっています。

今後の計画（想定）
- エグジット条件の追加（トレーリングストップ・時間決済等）
- execution / monitoring パッケージの具体実装（kabu ステーションとの連携、Slack 通知等）
- ai_scores を生成する NLP/ML パイプラインの統合
- 単体テスト・統合テストと CI 設定の整備

----------------------------------------

注: 本 CHANGELOG は与えられたコードの内容・コメント・ドキュメント文字列から自動的に要約したものであり、実際のコミット履歴や開発履歴と完全に一致しない場合があります。必要があれば、リポジトリの commit 履歴やリリースノートと照合して調整してください。