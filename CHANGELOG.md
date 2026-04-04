# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはパッケージの主要機能・設計上の重要な決定・フェイルセーフ挙動などをリリース単位でまとめたものです。

全般:
- パッケージバージョン: 0.1.0（src/kabusys/__init__.py の __version__ に準拠）
- 目的: 日本株自動売買プラットフォーム向けのデータ取得・ETL、リサーチ、AIベースのニュース解析・市場レジーム判定、運用設定管理を提供。

## [0.1.0] - 2026-04-04
初回リリース（初版機能セットを提供）

### Added
- パッケージ基盤
  - パッケージ公開インターフェースを定義（src/kabusys/__init__.py）
  - バージョン番号を 0.1.0 に設定

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env/.env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能
  - .env のパース機能（export プレフィックス対応、クォート内エスケープ、インラインコメント処理）
  - Settings クラスでアプリケーション設定をプロパティとして提供（J-Quants、kabu API、LINE、DB パス、監視設定、ログレベル、環境モード等）
  - 必須キー未設定時に ValueError を投げる _require 実装
  - 環境値検証（KABUSYS_ENV、LOG_LEVEL の許容値検査）

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - score_news(conn, target_date, api_key=None) によるニュース記事の銘柄別センチメント生成
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の記事を対象）を calc_news_window で提供
  - raw_news と news_symbols を結合して銘柄毎に記事を集約（最大記事数 / 文字数でトリム）
  - OpenAI (gpt-4o-mini) へバッチ送信（最大バッチサイズ 20 銘柄）
  - JSON Mode を用いたレスポンス処理、レスポンスの堅牢なバリデーション（JSON 抜き出し、results リスト、code/score 検査、数値変換）
  - リトライ/バックオフ戦略（429/ネットワーク/タイムアウト/5xx を対象に指数バックオフ）
  - スコアは ±1.0 にクリップし、DuckDB へ冪等的に書き込み（DELETE→INSERT）、部分失敗時に他銘柄の既存スコアを保護
  - テスト用フック: _call_openai_api を patch で差し替え可能

- AI 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - score_regime(conn, target_date, api_key=None) による日次レジーム評価（bull / neutral / bear）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成
  - ma200_ratio の算出（target_date 未満のデータのみ使用してルックアヘッドを防止）
  - マクロキーワードで raw_news のタイトルを抽出し、OpenAI でセンチメント評価
  - LLM 呼び出しでのリトライ・エラーハンドリング（API エラー時のフェイルセーフとして macro_sentiment=0.0 で継続）
  - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）

- データプラットフォーム（src/kabusys/data/*）
  - ETL パイプラインインターフェース（src/kabusys/data/pipeline.py）
    - ETLResult データクラス（ETL 実行メトリクス、品質問題、エラーの集約、ユーティリティ to_dict）
    - 差分取得・バックフィル方針、品質チェックの収集方針を実装方針として明示
    - DuckDB を前提としたテーブル存在チェック等のユーティリティ
  - ETL の公開再エクスポート（src/kabusys/data/etl.py: ETLResult を公開）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定 API を提供
    - market_calendar テーブルが存在しない場合は曜日ベースのフォールバック（週末を非営業日とする）
    - DB 登録値を優先し、未登録日は曜日フォールバックで補完する一貫したロジック
    - calendar_update_job により J-Quants API からの差分取得と冪等保存（バックフィル日数・健全性チェックを含む）
    - 最大探索日数の上限を設けて無限ループを防止

- リサーチ / ファクター群（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、ma200_dev（200日 MA に対する乖離）
    - calc_volatility(conn, target_date): atr_20、atr_pct、avg_turnover、volume_ratio（20日ベース）
    - calc_value(conn, target_date): PER、ROE（raw_financials の最新値を target_date 以前で参照）
    - 各計算は DuckDB の SQL を活用し、データ不足時は None を返す（無効銘柄を扱いやすくする）
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン計算（デフォルト [1,5,21]）
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）算出
    - rank(values): 同順位は平均ランクで扱うランク付け実装（丸めによる ties の扱いに配慮）
    - factor_summary(records, columns): count/mean/std/min/max/median を算出する統計サマリー
  - 研究系 API はすべて外部金融 API /発注 API にアクセスせず、DuckDB のみ参照

### Changed
- （初回リリースのため該当なし。今後のリリースで差分を記載）

### Fixed
- （初回リリースのため該当なし。バグ修正は次バージョンで明記）

### Notes / 設計上の重要点（リリース時の保証事項）
- ルックアヘッドバイアス対策: date.today()/datetime.today() などを直接参照しない実装方針を採用。全てのスコア・判定関数は引数の target_date を基準に処理します。
- フェイルセーフ: OpenAI や外部 API の失敗時は原則例外を投げずにスキップまたはデフォルト値（例: macro_sentiment=0.0）で継続するようにして、バッチ処理全体を停止させない設計。
- 冪等性: DB 書き込みは可能な限り冪等（DELETE→INSERT や ON CONFLICT）で行い、部分失敗が他データを破壊しないよう配慮。
- テスト容易性: OpenAI 呼び出し箇所は内部 _call_openai_api 関数に集約してあり、unittest.mock.patch による差し替えが可能。
- DuckDB 互換性: executemany の空リストバインド等、DuckDB の既知の挙動（バージョン差）に配慮した実装を行っている。

---

将来的に以下の点を CHANGELOG に追記してください:
- バグ修正 (Fixed)
- API 仕様変更や破壊的変更 (Changed / Removed)
- 新機能追加 (Added) やパフォーマンス改善 (Changed)
- セキュリティ修正 (Security)

もし特定のファイルや変更点をより詳細に記載したい場合は、対象箇所を指定してください。