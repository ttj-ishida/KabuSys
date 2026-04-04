# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。安定版リリースはセマンティックバージョニングに従います。

注: この CHANGELOG は提供されたコードベースから実装内容を推測して作成しています。

## [0.1.0] - 2026-04-04

### Added
- 初回リリース。日本株自動売買システム "KabuSys" の基礎機能を追加。
- パッケージ公開情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。
- 環境設定/ロード機能（kabusys.config）
  - .env / .env.local ファイルもしくは OS 環境変数から設定を読み込む自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - 読み込みの優先度: OS 環境変数 > .env.local > .env。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは export VAR=val 形式やシングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。
  - 設定値を取得する Settings クラスを提供（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定 など）。
  - 必須環境変数未設定時は ValueError を発生させる _require を実装。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP: src/kabusys/ai/news_nlp.py を追加
    - raw_news + news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）にバッチで問い合わせて銘柄単位のセンチメント(ai_score) を ai_scores テーブルに書き込む。
    - JST ベースのニュースウィンドウ計算（前日15:00〜当日08:30）を calc_news_window で提供。
    - API 呼び出しは JSON Mode を期待し、レスポンスの堅牢なバリデーションとスコアの ±1.0 クリップを実施。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライし、その他エラー時はフェイルセーフで該当チャンクをスキップ。
    - DuckDB の executemany の制約に配慮し、空リストの処理を回避する実装。
  - 市場レジーム判定: src/kabusys/ai/regime_detector.py を追加
    - ETF(1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - マクロニュースは raw_news から事前定義のキーワードで抽出し、OpenAI により JSON で macro_sentiment を取得。API 失敗時は 0.0 にフォールバック。
    - レジーム合成としきい値によるラベリングを実装。
    - OpenAI 呼び出しはモジュール独自実装として切り離し、テスト容易性を確保。

- データ基盤ユーティリティ（kabusys.data）
  - ETL パイプライン: src/kabusys/data/pipeline.py を追加
    - ETL 実行結果を表す ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得、保存（jquants_client 経由の冪等保存）、品質チェック（quality モジュールとの連携）を想定した設計。
    - 最終取得日やバックフィルロジック、品質問題の収集・表現方法を備える。
  - マーケットカレンダー管理: src/kabusys/data/calendar_management.py を追加
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - DB 登録がない場合の曜日ベースのフォールバック、DB 値優先の一貫した補完ロジックを実装。
    - 夜間バッチ更新 job (calendar_update_job) を実装し、J-Quants からの差分取得 → 保存（jq.save_market_calendar）を行う。バックフィル・健全性チェックを実装。
  - 公開インターフェース: ETLResult を kabusys.data.etl から再エクスポート。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュールを追加（calc_momentum, calc_volatility, calc_value）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20 日 ATR、ATR 比率、20日平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB の SQL と Python を組合せて計算。
    - データ不足時の扱い（None）やスキャン範囲バッファの考慮を実装。
  - feature_exploration モジュールを追加（calc_forward_returns, calc_ic, factor_summary, rank）
    - 将来リターンの計算（horizons の検証とまとめて取得）、IC（Spearman の ρ）計算、ファクター統計サマリー、平均ランクの実装を提供。
  - kabusys.research パッケージは主要 API を __all__ で公開。

### Changed
- 設計方針が明示
  - 主要な分析 / ETL / AI 関数は datetime.today()/date.today() を参照しない実装方針（ルックアヘッドバイアス防止）を採用。
  - OpenAI 呼び出しや DB 書き込みは冪等性・フェイルセーフを重視した実装。

### Fixed
- OpenAI レスポンスの堅牢な処理
  - JSON Mode でも前後に余計なテキストが混入するケースを想定して最外の {} を抽出してパースするフォールバックを実装。
- DuckDB 互換性
  - executemany に空リストを渡すとエラーになるケースへのガードを追加（空時は実行しない）。

### Security
- 環境変数の上書き制御
  - .env ファイル読み込み時、既存 OS 環境変数を保護するため protected セットを用いた上書き制御を実装。

### Internal / Misc
- ロギングの強化
  - 各主要処理において情報・警告・例外ログを適切に出力するように実装（API失敗時の詳細ログ、ROLLBACK 失敗時の警告など）。
- テストしやすさの配慮
  - OpenAI 呼び出し部分は内部で関数化し、unittest.mock.patch による差し替えが可能な設計。
- 型ヒントとドキュメンテーション
  - 各関数に詳細な docstring を追加（期待入力、返り値、エラー条件、設計方針の注記等）。

### Known limitations / TODO
- 一部ファクター（PBR、配当利回り）は未実装（calc_value の注記）。
- 外部モジュール（jquants_client, quality, monitoring 等）の実装詳細はこのスナップショットに含まれていないため、連携時の挙動はそちらに依存。
- 実運用時のスケジュール・監視・実行エンジン周り（execution, monitoring パッケージ）の具体実装は別途。

----

今後のリリースでは、発注・実行周りの実装（kabu ステーション連携）、モニタリングの拡充、追加ファクター／モデルの導入、テストカバレッジ拡大を予定しています。