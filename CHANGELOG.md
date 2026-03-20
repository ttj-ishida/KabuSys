Keep a Changelog
=================

すべての重要な変更点をこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠しています。

v0.1.0 - 2026-03-20
-------------------

Added
- パッケージ初期リリース。基本モジュールと主要機能を追加。
  - kabusys.config
    - .env ファイルおよび環境変数の自動読み込み機能（プロジェクトルートは .git / pyproject.toml を基準に探索）。
    - 行パーサは export KEY=val 形式、クォート内のエスケープ、インラインコメント等に対応。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、アプリ設定をプロパティ経由で取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - 値検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の許容値チェックを実装。
    - データベースパスのデフォルト（DUCKDB_PATH, SQLITE_PATH）をサポート。
  - kabusys.data.jquants_client
    - J-Quants API クライアントを実装（ページネーション対応）。
    - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対象）。429 の場合は Retry-After を考慮。
    - 401 応答時の自動トークンリフレッシュ（1回だけリトライ）とモジュールレベルの id_token キャッシュ。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供。
    - DuckDB への保存用ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、冪等性を保証（ON CONFLICT DO UPDATE）。
    - データ変換ユーティリティ _to_float / _to_int を実装（型安全・空値・不正値対策）。
  - kabusys.data.news_collector
    - RSS フィード収集モジュールを実装（既定ソースに Yahoo Finance を含む）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）、記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - XML パースに defusedxml を使用して XML ベース攻撃を軽減。
    - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）、SSRF 対策（HTTP/HTTPS 限定）等の安全対策を組み込み。
    - raw_news へのバルク保存時にチャンク処理を行い、トランザクションで効率化。
  - kabusys.research
    - ファクター計算および解析機能を提供（外部依存を極力排除、prices_daily/raw_financials のみ参照）。
    - kabusys.research.factor_research:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（200日データ不足時は None）。
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（ATR の欠損制御あり）。
      - calc_value: per, roe を raw_financials と価格から計算（EPS = 0/欠損は None）。
    - kabusys.research.feature_exploration:
      - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで計算。
      - calc_ic: スピアマンのランク相関（IC）を実装。サンプル不足（<3）や分散0の場合は None を返す。
      - factor_summary: count/mean/std/min/max/median を計算。
      - rank: 同順位は平均ランク扱い（丸め処理による ties 対応）。
    - zscore_normalize を外部モジュールからエクスポート（kabusys.data.stats 経由）。
  - kabusys.strategy
    - feature_engineering.build_features:
      - 研究モジュールから取得した生ファクターをマージし、ユニバースフィルタ（株価>=300円・20日平均売買代金>=5億円）を適用。
      - 指定カラムを Z スコア正規化、±3 でクリップし features テーブルへ日付単位で置換（削除→挿入、トランザクションで原子性保証）。
      - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用。
    - signal_generator.generate_signals:
      - features と ai_scores を統合して momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
      - デフォルト重みと閾値（default threshold=0.60）を実装、ユーザ重みの検証・正規化を行う。
      - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）で BUY を抑制。
      - BUY シグナル（score >= threshold）と SELL（ストップロス -8% / final_score < threshold）を生成し、signals テーブルへ日付単位で置換。
      - SELL 優先ポリシー: SELL 対象は BUY から除外してランクを再付与。
      - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止。
  - 共通
    - 日付単位の置換処理は各所でトランザクション＋バルク挿入により原子性・冪等性を確保。
    - ロギングを適切な箇所に配置（info/warning/debug）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- news_collector で defusedxml を使用し XML 攻撃対策を導入。
- RSS の受信サイズ上限と URL 検証によりメモリDoS / SSRF リスクを低減。
- J-Quants クライアントで認証トークン管理・自動リフレッシュ・レート制御を実装し、外部 API 利用時の誤用を抑制。

Notes / Known limitations
- execution パッケージは present だが実装は未提供（__init__.py のみ）。発注実装は別途必要。
- signal_generator のエグジット条件に関して、コード内コメントで以下の未実装点が明記されています:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有60営業日超過）
  これらは positions テーブルに peak_price / entry_date 等の列を追加したうえで実装が必要。
- news_collector の RSS フェッチ本体（ネットワーク取得ロジックの詳細な実装箇所）は省略されている可能性があるため、実運用前にフェッチ周りの実装とエラーハンドリングを確認してください。
- research モジュールは外部ライブラリ（pandas 等）に依存しないよう設計されていますが、大規模データでの性能検証や最適化は今後の課題です。
- 環境変数の自動読み込みはプロジェクトルート検出に依存するため、配布後や非標準的なプロジェクト構成下では KABUSYS_DISABLE_AUTO_ENV_LOAD を用いて明示的に制御してください。

Authors
- 初回実装: kabusys 開発チーム（コードベースの docstring と実装に基づき要約）

License
- リポジトリ内のライセンス表記に従ってください（本CHANGELOGはコード内容から推測して記載しています）。