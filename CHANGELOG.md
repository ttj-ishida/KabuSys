# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

最新版: 0.1.0 — 2026-03-20

## [Unreleased]

## [0.1.0] - 2026-03-20

### Added
- 初期リリースとして日本株自動売買ライブラリ "KabuSys" を追加。
- パッケージ公開情報
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - エクスポート: data / strategy / execution / monitoring を __all__ で公開。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）。
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パースの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート。
    - コメント判定ロジック（クォート内無視、非クォートでは '#' の前が空白/タブの場合のみコメントとみなす）。
  - Settings クラスで必須・既定設定をプロパティとして提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）。
  - 環境値検証（KABUSYS_ENV の有効値検査、LOG_LEVEL の検査）とユーティリティプロパティ（is_live / is_paper / is_dev）。
  - データベース既定パス（duckdb / sqlite）の展開。

- データ収集 / 保存モジュール（src/kabusys/data）
  - J-Quants クライアント（src/kabusys/data/jquants_client.py）
    - API 呼び出しラッパーを実装（固定間隔スロットリングによるレート制限: 120 req/min）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 発生時は自動でリフレッシュトークンから ID トークンを取得して 1 回だけリトライ。
    - ページネーション対応（pagination_key を用いた繰り返し取得）。
    - DuckDB への冪等保存ユーティリティ:
      - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE。
      - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE。
      - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE。
    - レスポンス JSON デコードエラーハンドリング、ログ出力。
    - 型変換ユーティリティ: _to_float / _to_int（文字列の浮動小数や空文字の扱いを明確化）。
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィードから記事を収集し raw_news へ冪等保存。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - 記事ID生成方針: 正規化 URL の SHA-256（先頭 32 文字）を利用して冪等性を保証。
    - セキュリティ対策:
      - defusedxml を使った XML パース（XML Bomb 等の防御）。
      - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
      - HTTP/HTTPS スキーム以外の URL を拒否し SSRF リスクを軽減。
    - バルク INSERT のチャンク処理で SQL 長やパラメータ数を制御。

- リサーチ / ファクター計算（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - モメンタムファクター（mom_1m, mom_3m, mom_6m, ma200_dev）を計算（200 日移動平均の存在チェック付き）。
    - ボラティリティ / 流動性（atr_20, atr_pct, avg_turnover, volume_ratio）を計算（true range の NULL 伝播制御、部分窓の扱い）。
    - バリューファクター（per, roe）を計算。raw_financials から target_date 以前の最新財務データを使用。
    - DuckDB SQL を主体とした実装で pandas 等に依存せずに動作。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 (calc_forward_returns)：1日/5日/21日等のホライズンに対応、ホライズンの妥当性検査あり。
    - IC（Information Coefficient）計算 (calc_ic)：Spearman の ρ をランク計算で実装（同順位は平均ランク）。
    - rank ユーティリティ：同順位の平均ランク付与、丸め（round(v,12)）で ties の誤検出を抑制。
    - factor_summary：count/mean/std/min/max/median を計算する統計サマリー。

- ストラテジー層（src/kabusys/strategy）
  - feature_engineering.build_features
    - research 側で計算した生ファクターを統合・正規化し features テーブルへ日付単位で置換（冪等）。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - トランザクション＋バルク挿入で原子性を確保。
  - signal_generator.generate_signals
    - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成、signals テーブルへ日付単位で置換（冪等）。
    - デフォルト重みと閾値を実装（デフォルト閾値 = 0.60、重みは momentum/value/volatility/liquidity/news）。
    - 重みの入力検証・スケーリング（未知キーや不正値は無視、合計が 1 でない場合は再スケール）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY を抑制）。サンプル数閾値あり。
    - SELL 判定ポリシー実装（ストップロス -8% 優先、final_score が閾値未満で SELL）。
    - SELL 優先ポリシーにより BUY から SELL 対象を除外しランクを再付与。
    - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止。

### Security
- news_collector で defusedxml を使用、RSS をパースする際の XML に対する安全性を確保。
- ニュース URL の正規化とトラッキングパラメータ除去によりノイズを低減。
- J-Quants クライアントでタイムアウト・エラーハンドリングを実装。

### Known issues / TODO
- signal_generator の SELL 判定に関して、コメントで記載されている以下の条件は未実装：
  - トレーリングストップ（peak_price の管理が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
  実装には positions テーブルに peak_price / entry_date 等の追加情報が必要。
- NewsCollector のさらに詳細な SSRF 防御（DNS レゾルバ制限やホワイトリストなど）は将来的検討事項。
- 一部ユーティリティは外部環境（DuckDB のスキーマ、テーブル定義）に依存するため、導入時にスキーマ準備が必須。

### Breaking Changes
- 初期リリースのため変更なし。

### Notes
- 実運用では KABUSYS_ENV を適切に設定し（development / paper_trading / live）、本番稼働時は is_live フラグやログレベルの設定に注意してください。
- .env の自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後も期待通りに動作させるには .git または pyproject.toml を含めるか、KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して外部管理に切り替えてください。

---

（この CHANGELOG はソースコードの実装内容とコメントから推測して作成しています。実際のリリースノートとして公開する前に、付随するドキュメントやリリース手順と整合性を取ることを推奨します。）