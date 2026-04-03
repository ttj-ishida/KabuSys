# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリースはセマンティックバージョニングに従います。

- https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-03

初期公開リリース。

### Added
- パッケージの基礎構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - エクスポート: data, strategy, execution, monitoring を公開 (将来的な拡張ポイント)

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装
    - プロジェクトルートの検出は .git または pyproject.toml を基準とし、CWD に依存しない。
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - ロード優先度: OS 環境変数 > .env.local > .env（.env.local は override=True）
    - OS 環境変数は protected として上書きされないよう保護
  - 高度な .env パーサを実装
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応
    - クォートなしの値でのインラインコメント処理（直前が空白/タブの '#' をコメントとして扱う）
  - Settings クラスを提供（settings インスタンスを公開）
    - 必須キーの確認を行う _require() を使用（未設定時は ValueError）
    - J-Quants / kabu ステーション / LINE / DB / 監視 / システム設定用プロパティを提供
    - デフォルト値、パス展開、型変換を行う（例: duckdb/sqlite のパス、閾値の float 変換）
    - KABUSYS_ENV と LOG_LEVEL の値検証（許可値集合による検証）
    - is_live / is_paper / is_dev の補助プロパティ

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP（センチメント） (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を用いてターゲットウィンドウの記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメントを取得
    - ウィンドウ定義: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）
    - バッチサイズ、トークン肥大化対策（銘柄あたり最大記事数・文字数）を実装
    - JSON Mode を利用した厳密な JSON レスポンス期待（レスポンスの復元ロジック含む）
    - 429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフとリトライ
    - レスポンス検証（results リスト・code/score 検証・スコアの ±1.0 クリップ）
    - 書き込みは部分失敗への耐性を考慮して、取得できた銘柄のみ DELETE → INSERT（トランザクション、Rollback 処理あり）
    - 公開関数: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム判定
    - マクロニュース抽出のためのマクロキーワードリストを実装
    - OpenAI（gpt-4o-mini）を利用した macro_sentiment 評価（JSON 出力期待）
    - API エラーやレスポンスパース失敗時はフェイルセーフで macro_sentiment = 0.0 を採用
    - レジームスコア合成、ラベル付与（bull / neutral / bear）、および market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - 公開関数: score_regime(conn, target_date, api_key=None)

- 研究（Research）モジュール (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - モメンタム: mom_1m / mom_3m / mom_6m、ma200_dev（200日MA乖離）を計算する calc_momentum()
      - データ不足時は None を返す方針
    - ボラティリティ/流動性: atr_20（20日 ATR）、atr_pct、avg_turnover、volume_ratio を計算する calc_volatility()
      - true_range の NULL 取り扱いに注意（不完全データでの過大評価を防止）
    - バリュー: latest_fin を参照して per（株価/EPS）および roe を計算する calc_value()
    - すべて DuckDB の prices_daily / raw_financials のみ参照（外部 API 非依存）
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons)
      - 複数ホライズンを一度のクエリで取得する実装
      - 引数 validation（horizons の範囲チェック）
    - IC（Information Coefficient）計算: calc_ic(factors, forwards, factor_col, return_col)（Spearman）
      - 必要レコードが少ない場合は None
    - ランク変換: rank(values)（同順位は平均ランク）
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median）
  - zscore_normalize はデータユーティリティ（kabusys.data.stats からの再エクスポート）を参照

- データプラットフォーム / ETL (src/kabusys/data/)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの夜間差分更新ジョブ calendar_update_job(conn, lookahead_days)
      - J-Quants API からの取得・保存（fetch/save は jquants_client へ委譲）
      - バックフィル（直近 _BACKFILL_DAYS 日）・健全性チェック（未来日付の異常検出）
    - 営業日判定ユーティリティ
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
      - DB 登録がない場合は曜日ベースのフォールバック（週末を非営業日）
      - 最大探索日数の上限設定で無限ループを防止
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - 差分取得・保存・品質チェックの枠組み（設計方針とデフォルトの backfill）
    - ETLResult データクラスを定義（取得数・保存数・品質問題・エラー情報を格納）
      - to_dict() により品質問題を辞書化して監査ログ等に利用可能
    - jquants_client と quality モジュールとの連携を想定
  - ETLResult は data.etl から再エクスポート（src/kabusys/data/etl.py）

- DB / トランザクション設計
  - DuckDB を前提とした SQL 実装（多くのクエリはウィンドウ関数を活用）
  - 書き込みは冪等性を重視（DELETE→INSERT のパターン）／トランザクション（BEGIN/COMMIT/ROLLBACK）で保護
  - DuckDB バージョンに依存する制約（executemany の空リスト不可等）に配慮した実装

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Notes / 設計上の重要な判断
- ルックアヘッドバイアス防止のため、各処理は datetime.today() / date.today() に依存しない設計を採用（呼び出し側から target_date を与える方式）。
- OpenAI 呼び出しは各モジュール内で独立実装し、モジュール間でのプライベート関数共有を避ける（テスト時に patch しやすいことを想定）。
- OpenAI のレスポンスや API 障害に対してはフェイルセーフを優先（ゼロやスキップで継続し、致命的な例外は上位へ伝播）。
- 多くの箇所で入力検証・ログ出力・警告処理を導入し、運用時のトラブルシュートを容易にする設計。

### Security
- API キー未設定時には ValueError を投げる明示的なチェックを実装（OPENAI_API_KEY の扱い）。
- 環境変数読み込み時に OS 環境変数を保護（上書き不可）する仕組みを提供。

---

貢献・バグ報告・改善案は issue/PR を通じて歓迎します。