# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※初期リリースの内容は、リポジトリ内のソースコードから推測して記載しています。

## [Unreleased]

---

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買システムのコアユーティリティ群（設定管理・データ処理・研究用ファクター計算・AI ベースのニュース解析・市場レジーム判定等）を提供します。

### Added
- パッケージのメタ情報と公開サブパッケージ
  - src/kabusys/__init__.py による version (0.1.0) と公開モジュール指定（data, strategy, execution, monitoring）。
- 環境変数／設定管理
  - src/kabusys/config.py
    - .env ファイル（.env, .env.local）をプロジェクトルートから自動ロードする仕組みを追加。プロジェクトルートは .git または pyproject.toml を基準に探索。
    - export KEY=val、クォート付き値（シングル・ダブル）やエスケープに対応した .env パーサを実装。
    - OS 環境変数を保護する protected 上書き制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 必須設定取得用の _require と Settings クラスを実装（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境・ログレベル検証など）。
    - KABUSYS_ENV / LOG_LEVEL に対する妥当性チェック（許容値のバリデーション）を実装。
- AI（ニュース NLP / レジーム検出）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を元にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄毎のセンチメント ai_score を計算、ai_scores テーブルへ書き込む。
    - チャンクサイズ、記事数・文字数上限、エクスポネンシャルバックオフ付きリトライ（429・ネットワーク断・タイムアウト・5xx）を実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造検証、未知コードの無視、数値チェック、±1.0 クリップ）。
    - DuckDB の executemany 周りの注意（空パラメータ回避）に配慮した安全な置換（DELETE → INSERT）ロジック。
    - テスト容易性のため _call_openai_api の差し替えを想定。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225 連動）200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出し market_regime テーブルへ冪等書き込み。
    - prices_daily のルックアヘッドバイアス防止（target_date 未満のデータのみ使用）設計。
    - OpenAI 呼び出しに対するリトライ（指数バックオフ）とフェイルセーフ（API 失敗時に macro_sentiment=0.0）。
    - API レスポンス JSON パース失敗時や非5xx エラーの扱いを明確化。
- データ関連ユーティリティ
  - src/kabusys/data/calendar_management.py
    - market_calendar を用いた営業日判定・前後営業日探索・期間内営業日列挙・SQ判定ロジックを実装。
    - DB にデータがない場合は曜日ベース（土日休み）でフォールバックする一貫性ある挙動。
    - next_trading_day / prev_trading_day の探索上限（_MAX_SEARCH_DAYS）と異常検出の挙動を実装。
    - calendar_update_job により J-Quants API から差分取得し冪等に保存（バックフィル・健全性チェック対応）。
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETLResult データクラスと ETL パイプラインの骨子（差分取得・保存・品質チェックを想定）を追加。
    - _get_max_date / _table_exists 等の DB ユーティリティを実装（ETLResult の to_dict による品質情報出力対応）。
- 研究（Research）関連
  - src/kabusys/research/factor_research.py
    - ファクター計算機能（モメンタム: 1M/3M/6M、200日 MA 乖離 / ボラティリティ: 20日 ATR、流動性: 平均売買代金等 / バリュー: PER・ROE）を実装。
    - DuckDB を用いた SQL ベースの高性能計算、データ不足時の None 処理やログ出力を考慮。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ランク化ユーティリティ、ファクター統計サマリを実装。
    - pandas 等外部ライブラリに依存しない純 Python 実装で、欠損・有限性チェックを行う。
  - src/kabusys/research/__init__.py：上記ユーティリティを公開。
- その他
  - テストや実運用を想定したログ出力、例外処理、DuckDB との相互作用に関する注意点や設計コメントを多数追加。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- AI 機能は OpenAI API キー（OPENAI_API_KEY）を環境変数または関数引数で受け取る設計。キーの管理は利用者側で行うことを前提としています（ソースコード/ログへの埋め込み禁止）。
- .env 自動ロード時に OS 環境変数を保護する設計（protected set により上書きを防止）。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定可能。

### Notes / Known limitations
- DuckDB 内の期待テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials 等）が存在することを前提に実行されます。テーブルがない場合やスキーマが異なる場合は例外が発生します。
- news_nlp / regime_detector の OpenAI 呼び出しは gpt-4o-mini と JSON Mode を前提とした実装。将来の SDK / モデル変更によりレスポンス形式や例外クラスが変化する可能性があります（コード内で一部互換性確保の工夫あり）。
- 設計上、datetime.today() / date.today() を直接参照しないことでルックアヘッドバイアスを防いでいます。すべての処理で target_date を明示的に渡すことが必要です。
- ETL / calendar_update_job は J-Quants クライアント（jquants_client）に依存しますが、本差分には jquants_client の実装は含まれていません（別モジュールとして存在する想定）。

---

今後の作業候補（ToDo）
- strategy / execution / monitoring の具体実装（現状は公開名のみ）。
- 単体テスト・統合テストの追加（特に OpenAI API 呼び出し部分のモックと DuckDB テストデータ）。
- ドキュメント（使い方・DB スキーマ・デプロイ手順）の整備。