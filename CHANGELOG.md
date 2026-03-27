# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
過去の変更履歴はセマンティックバージョニングに基づいています。

全体の概要:
- パッケージバージョン: 0.1.0
- 初期リリース（ベース機能の実装）

## [Unreleased]

## [0.1.0] - 2026-03-27

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py）。バージョンは `0.1.0`。公開モジュールは data / research / ai / ... を想定した __all__ を設定。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に行い、カレントワーキングディレクトリには依存しない仕様。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサーは `export KEY=val` 形式、シングル/ダブルクォート（バックスラッシュエスケープ対応）、コメント処理（クォート外の # の扱い）などをサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL等）のプロパティを公開。必須変数未設定時は明確な ValueError を送出。環境値の検証（env, log_level の許容値チェック）を実装。

- ニュースNLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を用いて銘柄ごとのセンチメント（ai_score）を生成する `score_news` を実装。
  - タイムウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）の定義を持ち、内部では UTC naive datetime に変換して DB 比較を行う（ルックアヘッドバイアス防止のため datetime.today() を直接参照しない設計）。
  - OpenAI（gpt-4o-mini）を JSON Mode で呼び出し、最大 20 銘柄 / バッチで処理。1 銘柄当たりの最大記事数・文字数制限（トークン肥大化対策）をサポート。
  - API の一時エラー（429、ネットワーク断、タイムアウト、5xx）に対して指数バックオフでリトライし、永久エラーや解析失敗はフェイルセーフでスキップ（例外を上げず処理継続）。
  - レスポンス検証ロジックを実装（JSON 抽出・キー検査・スコア数値性チェック・既知コードのみ採用）。スコアは ±1.0 にクリップ。
  - スコアの DB 書き込みは部分失敗を避けるため、取得済みコードのみ削除→挿入する冪等方式（トランザクション + executemany）。DuckDB の埋め込み制約（空パラメータの executemany 非対応）に配慮した実装。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM による、重み 30%）を合成し、日次で市場レジーム（"bull" / "neutral" / "bear"）を判定する `score_regime` を実装。
  - ma200 の計算は target_date 未満のデータのみを使用してルックアヘッドを防止。データ不足時のフォールバック（中立値 1.0）とログ出力を実装。
  - マクロ記事抽出はマクロキーワード群に基づいて raw_news からタイトルを取得。記事がある場合のみ OpenAI（gpt-4o-mini）に問い合わせ、JSON レスポンスから -1.0～1.0 の macro_sentiment を取得。
  - API 呼び出しは再試行・バックオフを実装。API 失敗やパース失敗時は macro_sentiment を 0.0 にフォールバックして処理を継続（フェイルセーフ）。
  - 最終的な regime_score をクリップして閾値判定し、market_regime テーブルに冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）する。

- データプラットフォーム（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理ロジックを実装。market_calendar テーブルを参照し、is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日ヘルパーを提供。
    - DB にカレンダー登録がない場合は曜日ベース（土日非営業）でフォールバックする一貫した挙動を実装。
    - 夜間バッチ更新ジョブ `calendar_update_job` を実装し、J-Quants クライアントから差分取得→保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）する処理を提供。バックフィルや健全性チェック（過剰に未来日が登録されている場合はスキップ）を実装。
  - ETL／パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL の結果を表す `ETLResult` dataclass を実装（取得数・保存数・品質問題・エラー列挙など）。to_dict により品質問題を簡易表現へ変換可能。
    - jquants_client を介した差分取得・保存および品質チェック（quality モジュール）を想定した設計。差分・バックフィル・idempotent 保存の方針を明記。
    - etl モジュールはパブリックに ETLResult を再エクスポート。

- リサーチ（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム、ボラティリティ（ATR・流動性）、バリュー（PER, ROE）の計算関数 `calc_momentum`, `calc_volatility`, `calc_value` を実装。全て DuckDB の prices_daily / raw_financials を参照し、外部 API に依存しない。
    - データ不足時の None 返却、200 日 MA のデータ検査など堅牢性を考慮した実装。
  - 特徴量探索・統計（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン・検証）、IC（Spearman ランク相関）を計算する `calc_ic`、ランク変換 `rank`、および統計サマリー `factor_summary` を実装。
    - pandas 等外部ライブラリに依存せず標準ライブラリ + DuckDB での実装を採用。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security / Operational notes
- OpenAI API キーの取り扱いは引数注入または環境変数 `OPENAI_API_KEY` を使用。未設定時は ValueError を送出し早期に検出。
- OpenAI 呼び出しは冪等・再試行・フェイルセーフを備えているが、実運用でのレート制限やコストに注意。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後や別配置での動作は `KABUSYS_DISABLE_AUTO_ENV_LOAD` により制御可能。

### Known issues / Limitations
- DuckDB のバインドや executemany の挙動に依存する箇所があり、古い DuckDB バージョンでは互換性の問題が生じる可能性がある（コード中に回避策あり）。
- 現時点で PBR や配当利回りなど一部のバリューメトリクスは未実装（calc_value に注記あり）。
- News/Regime モジュールは LLM レスポンスに依存するため、モデル変更や応答フォーマットの変化に対して脆弱。テスト用に内部の API 呼び出しをパッチ可能にしてある（unittest.mock.patch による差し替え想定）。

---

（初回リリース。以降の変更はこのファイルに時系列で追記してください。）