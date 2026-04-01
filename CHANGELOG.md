# Changelog

すべての変更は Keep a Changelog 準拠で記録します。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（未リリースの変更はここに記載）

## [0.1.0] - 初回リリース
初回公開リリース。以下の主要機能とモジュールを実装しました。

### Added
- パッケージ基盤
  - パッケージメタ情報 (src/kabusys/__init__.py) とバージョン 0.1.0 を追加。
  - モジュール群のエクスポート設定: data, strategy, execution, monitoring（公開 API）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード（OS 環境変数 > .env.local > .env の優先順位）。テスト用途に KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
  - .env パーサを実装：export キーワード対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いを考慮。
  - 環境変数必須チェック用のヘルパー _require、および各種設定プロパティ（J-Quants / kabu / Slack / DB パス / 監視閾値 / env/log_level 判定等）。
  - 環境値の妥当性検証（KABUSYS_ENV、LOG_LEVEL の許容値チェック）。

- AI / ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメント解析して ai_scores テーブルへ書き込む機能を実装（score_news）。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当）とその UTC 変換を提供（calc_news_window）。
  - バッチ処理（1 API コールあたり最大 20 銘柄）、1 銘柄当たりの記事数上限 / 文字数上限によるトリム実装。
  - API 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）と失敗時のフェイルセーフ（失敗したチャンクはスキップ）。
  - レスポンスの厳密なバリデーション（JSON 抽出、results 配列・code/score 検証、スコアの ±1.0 クリップ、未知コード無視）。
  - テスト容易性のため OpenAI 呼び出し点を差し替え可能に設計。

- AI / 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する機能（score_regime）。
  - ma200_ratio 計算（target_date 未満のデータを使用してルックアヘッドを防止）、マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini, JSON Mode）での macro_sentiment 推定。
  - API 失敗やパース失敗時は macro_sentiment=0.0 として継続するフェイルセーフを実装。リトライ/バックオフ処理あり。
  - 計算結果を market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- データプラットフォーム（Data）機能
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）、market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 情報がない場合の曜日ベースフォールバック（週末は非営業日）。DB に登録された値を優先する一貫したロジック。
    - バックフィル / 健全性チェック / 最大探索日数の制限を実装。
    - J-Quants クライアント経由でデータ取得・保存する設計（jq.fetch_market_calendar / jq.save_market_calendar）。

  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を実装し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を構造化して保持可能に。
    - ETL の設計方針を反映：差分取得、自動バックフィル、品質チェック（quality モジュール）を想定。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ / ファクター計算 (src/kabusys/research/*)
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高変化率）、バリュー（PER, ROE）を計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の SQL ウィンドウ関数と Python を組み合わせて実装。データ不足時の None 処理など堅牢性を確保。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装し、ランク同順位は平均ランクで処理。

- 研究ユーティリティの再エクスポート (src/kabusys/research/__init__.py)
  - 主要関数群を外部公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- （該当なし：初回リリースのため過去変更はありません）

### Fixed
- （該当なし：初回リリースのため過去不具合修正履歴はありません）

### Design / Implementation Notes（設計上の重要点）
- ルックアヘッドバイアス対策：いずれのアルゴリズム（ニューススコアリング、レジーム判定、ファクター計算等）も datetime.today() / date.today() を内部参照せず、target_date パラメータに依存する設計。
- DB 操作は冪等性を重視（DELETE→INSERT、ON CONFLICT 或いは明示的な置換ロジック）。
- OpenAI 呼び出しは JSON Mode（厳密 JSON 出力）を期待するが、パース失敗時のフォールバック（文字列内の最外側 {} 抽出等）を実装。
- API 障害時は安全に継続する（マクロセンチメント＝0.0、失敗チャンクスキップ等）方針で設計。
- DuckDB を主要な解析・中間格納 DB として想定（各関数は DuckDB 接続オブジェクトを受け取る）。
- .env ロード処理は配布後も期待通り動作するように __file__ を起点にプロジェクトルート (.git または pyproject.toml) を探索している。

### Known limitations / TODO
- Strategy / execution / monitoring の具象実装（発注ロジックや実行モジュール）は本リリースで未実装（パッケージ内に名前空間はあるが具体的ファイルは含まれていない）。
- 一部関数は外部モジュール（jquants_client, quality 等）に依存するため、これらの実体実装／モックが必要。
- OpenAI モデルは gpt-4o-mini を使用（API 利用料金・レイテンシに注意）。

---

（注）本 CHANGELOG はコードベースの現在の実装から推定して作成しています。実際のリリースノートに含める内容は、リリースプロセスや公開ポリシーに応じて調整してください。