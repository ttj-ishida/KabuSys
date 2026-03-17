CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

[0.1.0] - 2026-03-17
-------------------

初回公開リリース。日本株自動売買システムのコアライブラリとデータプラットフォーム用の基盤機能を実装しました。

### 追加 (Added)
- パッケージメタ
  - kabusys パッケージ初期版を追加（__version__ == 0.1.0）。
  - data, strategy, execution, monitoring を公開モジュールとしてエクスポート。

- 環境設定管理 (kabusys.config)
  - .env / .env.local / OS 環境変数からの自動読み込み機能を実装。
    - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml によって行うため、CWD に依存しない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env の行パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）。
  - Settings クラスを実装し、アプリケーション設定（J-Quants トークン、kabu API、Slack、DB パス、環境名・ログレベル等）の取得とバリデーションを提供。
  - 環境値の検証: KABUSYS_ENV と LOG_LEVEL に対する許容値チェック。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - レート制限用の固定間隔スロットリング実装（120 req/min を遵守）。
  - 再試行ロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx）、及び 429 の場合に Retry-After を尊重。
  - 401 受信時の ID トークン自動リフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ（ページネーション間共有）。
  - DuckDB へ保存する save_* 関数群を実装（raw_prices, raw_financials, market_calendar）。ON CONFLICT DO UPDATE により冪等性を担保。
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead bias を防止。
  - 型安全な数値変換ユーティリティ（_to_float / _to_int）を提供（空値・不正値ハンドリング、"1.0" のような float 文字列の int 変換時の厳格処理等）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集し、前処理 → raw_news へ冪等保存 → 銘柄コード紐付け（news_symbols）までを実現する一連の処理を実装。
  - 記事IDは URL 正規化後の SHA-256（先頭 32 文字）で生成し冪等性を保証。トラッキングパラメータ（utm_* 等）を除去してから正規化。
  - defusedxml を用いて XML Bomb 等の攻撃を防止。
  - SSRF 対策を強化:
    - URL スキーム検証（http/https のみ許可）。
    - ホスト/IP のプライベート判定（IP 直解析 + DNS 解決による A/AAAA 検査）。
    - リダイレクト時にスキームとホストを事前検査するカスタム RedirectHandler を実装。
  - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）や gzip 解凍後のサイズチェックを導入してメモリ DoS を緩和。
  - RSS の pubDate パース、テキスト前処理（URL 除去・空白正規化）を実装。
  - DB 保存はトランザクションでまとめ、INSERT ... RETURNING を用いて実際に挿入された記事 ID や挿入件数を正確に取得。
  - 銘柄コード抽出ユーティリティ（4桁数字パターン）と既知コードセットによるフィルタリングを提供。
  - run_news_collection により複数ソースの独立処理（1ソース失敗しても他は継続）を実現。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の層に基づいた包括的なテーブル定義を追加。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種 CHECK 制約、PRIMARY KEY、FOREIGN KEY を定義してデータ品質を強化。
  - クエリパターンに基づくインデックスを作成。
  - init_schema 関数でディレクトリ自動作成（必要に応じ）→ テーブル作成（冪等）→ 接続返却を実装。
  - get_connection で既存 DB への接続を提供（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新に基づく ETL の基幹機能を実装。
    - DB の最終取得日を基に差分（未取得範囲）を算出。
    - backfill_days による過去再取得（API の後出し修正吸収）。
    - 市場カレンダーの先読み等の設定（定数として _CALENDAR_LOOKAHEAD_DAYS 等）。
  - ETLResult dataclass を実装し、実行結果（取得/保存件数、品質問題、エラー一覧）を表現。
  - テーブル存在チェック・最大日付取得のユーティリティを実装。
  - _adjust_to_trading_day 等のカレンダーヘルパーを実装。
  - run_prices_etl の骨組みを実装（fetch → save の流れ）。品質チェック連携のためのフック（quality モジュール想定）を明示。

### 変更 (Changed)
- （初回リリースのためなし）

### 修正 (Fixed)
- （初回リリースのためなし）

### セキュリティ (Security)
- XML パースに defusedxml を使用して XML 関連の攻撃を緩和。
- RSS フェッチに対して SSRF 対策を導入（スキーム検証、プライベート IP 検出、リダイレクト検査）。
- RSS レスポンスサイズ上限と gzip 解凍後チェックを導入してメモリ DoS を緩和。

### 注意事項 / 既知の制約 (Notes / Known Issues)
- quality モジュール（欠損・スパイク・重複検出）の実装はパイプライン設計に組み込む前提で参照されているが、本リリースでの具体的なチェック一覧・実装詳細は別モジュールで提供される想定です。
- ETL の一部（例: run_prices_etl の戻り値整形や追加のエラーハンドリング等）は将来的な拡張対象です。
- DuckDB の SQL 実行においては埋め込み SQL 文字列を利用している箇所があり、プレースホルダでのパラメタライズと併用しています。既知の入力に対しては安全措置を講じていますが、運用時は接続権限とファイルアクセス権限の適切な制御を推奨します。

今後の予定
----------
- quality モジュールの実装とパイプライン統合（品質チェックの詳細ルールと自動アラート）。
- strategy / execution 層の実装（信号生成 → 注文送信 → 約定管理 → ポートフォリオ管理）。
- モニタリング（Slack 通知、メトリクス公開）・運用向けドキュメントの整備。
- 単体テスト／統合テストの追加と CI パイプライン整備。

-----