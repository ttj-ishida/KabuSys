CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
このファイルはコードベース（src/kabusys 以下）の現状から推測して作成した変更履歴です。

フォーマット:
- Unreleased: 今後の変更予定 / 既知の未実装事項
- 各リリース: 追加 (Added) / 変更 (Changed) / 修正 (Fixed) / 削除 (Removed) / セキュリティ (Security)

Unreleased
----------
- 予定・既知の未実装/改善点（コード内コメントから推測）
  - エグジット条件におけるトレーリングストップおよび時間決済の実装予定（positions テーブルに peak_price / entry_date の追加が必要）。
  - execution 層（発注ロジック）の実装（現状 src/kabusys/execution は空のパッケージ）。
  - 一部アノマリーやエッジケースの追加テスト強化（ネットワーク障害時のリトライ挙動、DBトランザクションのエラーケース等）。
  - news_collector の RSS ソース拡充とニュース→銘柄紐付け（news_symbols）ロジックの拡張。
  - 外部 API 呼び出しのモック／テスト用フック強化（get_id_token のテスト容易化など）。

[0.1.0] - 2026-03-20
-------------------
Added
- パッケージ初期構成を追加
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"、__all__ に主要モジュールを公開。
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml により判定）。
  - 読み込み順序: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env のパース機能を強化:
    - export KEY=val 形式対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理対応
    - インラインコメントの取り扱い（クォート有無に応じたルール）
    - 読み込み時に OS 環境変数の保護（protected set）をサポートし、override オプションを提供
  - Settings クラスを提供（J-Quants トークン、kabu API パスワード、Slack トークン・チャンネル、データベースパス等を環境変数から取得）。
  - env / log_level の値検証（許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）を追加。
- Data モジュール: J-Quants クライアント (kabusys.data.jquants_client)
  - API レート制御（_RateLimiter）を実装（120 req/min 固定間隔スロットリング）。
  - HTTP リクエストユーティリティ（_request）を実装:
    - ペイロード送信、JSON デコード、エラーハンドリング
    - 再試行（指数バックオフ、最大 3 回）とステータスコードによる制御（408/429/5xx）
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）とトークンキャッシュ共有
    - ページネーション対応（pagination_key）
  - API の高水準関数を実装:
    - get_id_token（リフレッシュトークンから ID トークン取得）
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - DuckDB への永続化ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar（冪等性を保つため ON CONFLICT DO UPDATE を使用）
    - レコードの型変換ユーティリティ (_to_float, _to_int)
    - PK 欠損レコードのスキップと警告出力
- Data モジュール: ニュース収集 (kabusys.data.news_collector)
  - RSS フィード取得・パース機能（defusedxml を利用し安全に XML を解析）
  - 記事 ID を URL 正規化後の SHA-256 ハッシュで生成（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント削除、キーソート）
  - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES）によるメモリ DoS 対策
  - URL の安全性チェック（HTTP/HTTPS）、SSRF 対策、IP アドレス検査などを想定した設計
  - raw_news への冪等保存（ON CONFLICT DO NOTHING）とバルク挿入チャンク制御
- Research モジュール (kabusys.research)
  - ファクター計算 (factor_research):
    - calc_momentum（1M/3M/6M リターン、MA200 乖離率）
    - calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）
    - calc_value（PER / ROE。raw_financials の最新レコードを参照）
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照
  - 特徴量探索 (feature_exploration):
    - calc_forward_returns（将来リターン計算、任意ホライズン、営業日を想定したバッファ）
    - calc_ic（Spearman ランク相関による IC 計算）
    - factor_summary（基本統計量: count/mean/std/min/max/median）
    - rank（同位順位は平均ランクで処理、丸めにより ties 検出の安定化）
  - zscore_normalize を data.stats から利用可能にするエクスポート
  - 研究コードは外部ライブラリ（pandas 等）に依存しない実装方針
- Strategy モジュール (kabusys.strategy)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research モジュールから取得した生ファクターをマージ
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）
    - Z スコア正規化（指定カラム）と ±3 でクリップ
    - DuckDB の features テーブルへ日付単位で置換（BEGIN / DELETE / INSERT / COMMIT、失敗時はロールバック）
    - 冪等性を意識した設計
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して最終スコア final_score を計算（momentum/value/volatility/liquidity/news の重み付け）
    - 重みの入力検証と合計が 1.0 になるよう正規化、無効値はスキップし既定値にフォールバック
    - AI レジームスコアの集計から Bear 相場判定（サンプル閾値あり）。Bear 相場時は BUY を抑制
    - BUY シグナル生成（閾値デフォルト 0.60）
    - SELL シグナル（ストップロス -8% / score 下落）判定の実装
    - signals テーブルへの日付単位置換（トランザクション処理）
    - エッジケース: features に存在しない保有銘柄は final_score=0 で扱う、安全重視の挙動
- ロギング / エラーハンドリング
  - 各所で logger を用いた情報・警告・デバッグ出力を追加（処理数や異常時の詳細ログ）
  - トランザクション失敗時のロールバック試行とロールバック失敗の警告

Changed
- 初期リリースにつき該当なし（初回導入）

Fixed
- 初期リリースにつき該当なし（初回導入）

Removed
- 初期リリースにつき該当なし（初回導入）

Security
- news_collector で defusedxml を使用し XML 攻撃（XML bomb 等）への耐性を確保
- news_collector で受信サイズ制限、URL 正規化、スキームチェックにより SSRF / メモリ DoS を緩和
- jquants_client でトークン管理と再試行の制御を行い不適切な再帰や無限ループを回避

Notes / 実装上の注意
- DuckDB への書き込みは冪等性を意識しているが、外部スキーマ（テーブル定義）やインデックス等はこの変更履歴の対象外。運用前にデータベースのスキーマを準備してください。
- positions テーブルに peak_price / entry_date 等がないとトレーリングストップや時間決済は未実装のままです。
- execution（発注）層は現状未実装のため、signals テーブル出力後の実取引には別実装が必要です。
- 一部処理（特にネットワーク／DB周り）はリトライ・ロールバックの仕組みが含まれるが、運用環境での負荷やサイドエフェクトについて事前テストを推奨します。

作者/貢献者
- コードベースの内容から推測して記載しています（自動生成ドキュメントではありません）。実際の開発履歴やコミットログがある場合はそちらを優先して CHANGELOG を更新してください。