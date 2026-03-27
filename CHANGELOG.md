# Changelog

すべての注目すべき変更はこのファイルに記録します。本ファイルは「Keep a Changelog」準拠の形式を採用します。

現在のリリース方針:
- バージョニングは SemVer を想定しています（本リポジトリの __version__ は 0.1.0）。
- 初期リリースは機能群の初回実装をまとめたものです。

※ 日付はコード解析時点の推定リリース日です。

## [Unreleased]
- （未リリースの変更はここに記載）

## [0.1.0] - 2026-03-27
最初の公開リリース。プロジェクトのコア機能（環境設定、データ基盤ユーティリティ、研究用ファクター計算、ニュース・AI スコアリング、マーケットレジーム判定、ETL/カレンダー管理）を実装。

### 追加（Added）
- パッケージのエントリポイントを追加
  - src/kabusys/__init__.py にてパッケージの公開モジュールを定義（data, strategy, execution, monitoring）。
  - バージョン情報 __version__ = "0.1.0" を追加。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - .env の行パーサ（クォート、エスケープ、export プレフィックス、インラインコメント対応）を実装。
    - OS 環境変数を保護する protected 上書き制御を実装（.env.local を上書き可能）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - Settings クラスを実装し、J-Quants / kabu / Slack / DB パス / 動作モード / ログレベルなどのプロパティとバリデーションを提供。

- AI（ニュース NLP と市場レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini + JSON Mode）で銘柄ごとのセンチメントスコアを算出して ai_scores テーブルへ保存する機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算（calc_news_window）。
    - バッチ処理、最大記事数・文字数トリム、チャンク送信（_BATCH_SIZE）をサポート。
    - API エラー（429 / ネットワーク / タイムアウト / 5xx）に対する指数バックオフリトライを実装。
    - レスポンスバリデーションと冗長な JSON パース耐性（前後余計なテキストから最外側の {} を抽出）を実装。
    - DuckDB 互換性のため executemany に空リストを渡さない保護処理を実装（DuckDB 0.10 対策）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する機能を実装。
    - prices_daily / raw_news を参照し、ma200_ratio の計算、マクロキーワードによる記事抽出、OpenAI 呼び出し（独自の実装）による macro_sentiment 評価、合成スコア算出、market_regime への冪等書き込みを実装。
    - API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを採用。
    - OpenAI 呼び出しは最大リトライ、指数バックオフ、5xx と非5xx の判別処理を実装。
    - ルックアヘッドバイアス防止のため date 参照は引数ベース（datetime.today()/date.today() を使用しない）。

- 研究（Research）モジュール
  - src/kabusys/research/
    - factor_research.py: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金 / 出来高比）およびバリュー（PER, ROE）計算を実装。DuckDB 上で SQL を組み合わせて計算し、日付・コード単位の結果を返却。
    - feature_exploration.py: 将来リターン calc_forward_returns（任意ホライズン対応）、IC（Spearman ランク相関）calc_ic、rank、factor_summary（count/mean/std/min/max/median）を実装。外部ライブラリに依存せず純標準ライブラリで実装。
    - research パッケージ __init__ で主要関数を公開（zscore_normalize は data.stats から再利用）。

- データ基盤（Data）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日（土日）ベースのフォールバックを行う一貫した方針を実装。
    - calendar_update_job: J-Quants API から差分取得して market_calendar に冪等保存。バックフィル、先読み、健全性チェック（未来の日付異常検知）を実装。
  - src/kabusys/data/pipeline.py / etl.py / __init__.py
    - ETLResult データクラスを実装し、ETL 実行結果の集約（取得数、保存数、品質問題、エラー等）を提供。
    - 差分更新、backfill、品質チェック連携を想定した ETL 用ユーティリティ（テーブル存在チェック、最大日付取得など）を実装。
    - data.etl は pipeline.ETLResult を再エクスポート。

- その他
  - DuckDB を前提とした SQL 実装（DuckDBPyConnection 型注釈）。
  - 詳細なロギング・警告メッセージを多く追加してトラブルシュートを容易化。

### 変更（Changed）
- （初回リリースのため過去バージョンからの変更点なし。設計上の決定点を明記）
  - 各 AI モジュール／ETL モジュールともに「ルックアヘッドバイアスを避ける」設計方針を採用（内部で現在時刻を参照せず、target_date 引数ベースで処理）。
  - OpenAI 呼び出しは JSON mode を使いレスポンスの構造化を強制する実装とし、パース失敗時の安全なフォールバック（スコア 0.0 やスキップ）を適用。
  - DuckDB のバージョン差異（executemany の空リストなど）に配慮した互換性対策を実装。

### 修正（Fixed）
- パーサ・パース耐性の改善
  - .env 行パーサが export プレフィックス・クォート内のエスケープ・インラインコメントを正しく扱うように実装。
  - OpenAI レスポンスの JSON パース失敗時に外側の波括弧を抽出して復元するロジックを追加し、レスポンスのノイズに対する耐性を向上。
- API 呼び出しの堅牢化
  - RateLimitError/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライする実装を追加し、一時的な障害に対する耐障害性を向上。
  - 永続的エラーや非再試行エラーはログ警告を出して安全にフォールバック（例: macro_sentiment=0.0、該当チャンクをスキップ）。

### 非推奨（Deprecated）
- なし（初回リリース）

### 削除（Removed）
- なし（初回リリース）

### セキュリティ（Security）
- OpenAI API キーは関数引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY を参照する方式。API キーの直接埋め込みは行わない設計。
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト用）。

---

開発・運用上の注意点（実装から推測）
- OpenAI 利用は gpt-4o-mini を想定しており、レスポンスの構造は厳密な JSON を要求している。API バージョン差やレスポンス形式変更に注意。
- DuckDB 依存の SQL 文はバージョン差異で動作が変わる可能性がある（executemany の空リスト等）。運用環境の DuckDB バージョンでの動作確認を推奨。
- データベースへの書き込みは冪等性を保つため DELETE→INSERT（BEGIN/COMMIT）の形を採っているが、大量データや並列処理時のロック/競合には注意が必要。
- 本リリースは多数の機能を含む初回実装のため、将来的に API 応答形式や外部サービスの変更に応じた微修正が想定されます。