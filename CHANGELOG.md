CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

0.1.0 - 2026-03-20
------------------

Added
- 初回リリース。パッケージ名: kabusys（日本株自動売買システムのコアライブラリ）。
- 環境設定:
  - kabusys.config: .env ファイルおよび環境変数から設定を読み込むユーティリティを追加。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）。
    - .env 自動ロード（優先順位: OS 環境 > .env.local > .env）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 複雑な .env パースロジック（export プレフィックス、クォート内のエスケープ、インラインコメント処理など）。
    - Settings クラス（J-Quants トークン、kabu API、Slack、DB パス、環境種別、ログレベル等のプロパティとバリデーション）。
- データ取得・保存:
  - kabusys.data.jquants_client:
    - J-Quants API クライアントを実装。ページネーション対応の fetch_* 関数（株価・財務・マーケットカレンダー）。
    - レートリミッタ（120 req/min 固定間隔スロットリング）実装。
    - 再試行（指数バックオフ、最大 3 回）と 401 の自動トークンリフレッシュ対応。
    - DuckDB への冪等保存ロジック（ON CONFLICT DO UPDATE を活用した save_* 関数: raw_prices, raw_financials, market_calendar）。
    - データ変換ユーティリティ（型変換の厳格化: _to_float / _to_int）。
  - kabusys.data.news_collector:
    - RSS フィードからニュースを収集するモジュールを追加。
    - URL 正規化（トラッキングパラメータ除去、クエリ整列、フラグメント除去）、記事 ID は正規化 URL の SHA-256 による生成（先頭 32 文字）で冪等性を確保。
    - defusedxml による XML パースでセキュリティ対策を実施。
    - 最大受信バイト数制限、HTTP スキーム検証、SSRF/メモリ DoS を意識した実装。
    - raw_news テーブルへのバルク保存を意識したチャンク処理とトランザクション設計。
- 研究用ユーティリティ（Research 環境向け）:
  - kabusys.research.factor_research:
    - モメンタム(calc_momentum)、ボラティリティ/流動性(calc_volatility)、バリュー(calc_value) のファクター計算実装。
    - prices_daily / raw_financials に対する SQL ベースの計算（移動平均、ATR、売買代金平均、PER など）。
    - データ不足時の None ハンドリング。
  - kabusys.research.feature_exploration:
    - 将来リターン計算(calc_forward_returns)、IC（スピアマンρ）計算(calc_ic)、ファクター統計要約(factor_summary)、ランク化(rank) を実装。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で完結。
  - research パッケージの __all__ を整備（外部公開 API を整理）。
- 戦略ロジック:
  - kabusys.strategy.feature_engineering:
    - 研究側の生ファクターを取り込み、ユニバースフィルタ（最低株価・平均売買代金）を適用後に Z スコア正規化し ±3 でクリップ、features テーブルへ日付単位で置換（冪等）する build_features を実装。
    - DuckDB トランザクションを使った原子更新を実施。
  - kabusys.strategy.signal_generator:
    - features と ai_scores を統合して最終スコア（final_score）を計算し BUY/SELL シグナルを生成する generate_signals を実装。
    - コンポーネントスコア（momentum、value、volatility、liquidity、news）の計算、シグモイド変換、欠損補完（中立値 0.5）。
    - 重みの補完・正規化・検証ロジック。デフォルト重みと閾値（デフォルト BUY 閾値 0.60）を採用。
    - Bear レジーム判定（ai_scores の regime_score に基づく平均判定）により BUY を抑制。
    - エグジット（SELL）判定ロジック（ストップロス -8%、スコア低下）を実装。SELL 優先ポリシー（SELL 対象を BUY から除外）を適用。
    - signals テーブルへの日付単位での置換（トランザクション＋バルク挿入）で冪等性と原子性を確保。
- パッケージ公開 API:
  - kabusys.__init__ に主要サブパッケージ名を追加し、トップレベルからアクセス可能に。

Security
- news_collector で defusedxml を採用し XML Bomb 等への対策を実施。
- news_collector は受信サイズ上限、HTTP/HTTPS スキーム制限、トラッキングパラメータ削除などで SSRF / 情報漏洩リスクを低減。
- jquants_client の HTTP リクエスト処理でタイムアウト、リトライ、429 の Retry-After 対応を考慮。

Notes / Design decisions
- ルックアヘッドバイアス回避: research/ と strategy/ の処理は target_date 時点で利用可能なデータのみを使用する設計（fetched_at を UTC で記録）。
- 冪等性: API 取得後の DB 保存や features/signals の書き換えは「日付単位の置換（DELETE→INSERT）」や ON CONFLICT を用いて冪等化。
- トランザクション: features / signals の更新は BEGIN/COMMIT/ROLLBACK を使い原子性を保つ実装。
- エラー・欠損データへの耐性: None / 非有限数の扱い、データ不足時の中立補完やスキップ等を行い誤判定を低減。

Changed
- （該当なし: 初回リリースのため過去の変更はなし）

Fixed
- （該当なし: 初回リリースのため過去の不具合修正履歴はなし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- 上記 Security セクションを参照。

---

注: 本 CHANGELOG はコードベースの実装内容から推測して作成したものであり、実際のリリースノートはリポジトリのコミットログや公開リリース情報に基づいて調整してください。