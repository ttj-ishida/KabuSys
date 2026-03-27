# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

次の表記規則に従います:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除
- Security: セキュリティ関連

## [Unreleased]

（現在なし）

---

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買・データ基盤・リサーチ用ユーティリティ群を提供します。

### Added
- パッケージ基盤
  - kabusys パッケージエントリポイントを追加（__version__ = 0.1.0、公開モジュール: data, strategy, execution, monitoring）。
- 設定管理
  - kabusys.config: .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの検出は .git または pyproject.toml を探索して行うため、CWD に依存しない挙動。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - export KEY=val 形式やクォート・エスケープ・行末コメントなどの .env パースをサポート。
    - 必須変数取得ヘルパー _require と Settings クラスを提供（J-Quants / kabuAPI / Slack / DB パス等のプロパティを公開）。
    - 設定値検証（KABUSYS_ENV, LOG_LEVEL の許容値検査）および is_live/is_paper/is_dev のブールプロパティを追加。
- データプラットフォーム（DuckDB ベース）
  - kabusys.data.pipeline:
    - ETL パイプラインの結果を表す ETLResult データクラスを公開（フェッチ・保存数、品質問題、エラー収集、シリアライズ用 to_dict）。
    - 差分取得・バックフィル・品質チェックを想定した設計。
  - kabusys.data.etl: ETLResult の再エクスポート。
  - kabusys.data.calendar_management:
    - JPX カレンダーの管理（market_calendar テーブル）と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - calendar_update_job: J-Quants からの差分取得と冪等保存ロジック、バックフィル・健全性チェック対応。
    - market_calendar 未取得時の曜日ベースフォールバックを実装。
- リサーチ用ユーティリティ
  - kabusys.research パッケージと各種関数を追加（再エクスポート含む）。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対ATR(atr_pct)、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials に基づく PER / ROE の計算。target_date 以前の最新財務データを使用。
    - 設計上、DuckDB の prices_daily / raw_financials のみ参照し実際の発注等にはアクセスしない仕様。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を利用）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。サンプル数不足時は None を返す。
    - rank: 同順位は平均ランクを与えるランク変換ユーティリティ（丸め処理で ties 問題に対応）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能。
- AI（自然言語処理）機能
  - kabusys.ai パッケージを追加。OpenAI（gpt-4o-mini）を用いた JSON Mode 呼び出しに対応。
  - news_nlp:
    - score_news: raw_news と news_symbols を集約し、銘柄ごとにニュースのセンチメントを LLM で評価して ai_scores テーブルへ書き込む。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄/コール）、記事・文字数トリミング、JSON レスポンスのバリデーション、数値クリッピング（±1.0）、エラー時のフェイルセーフ（スキップ）およびリトライ（429・ネットワーク・5xx の指数バックオフ）を実装。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
  - regime_detector:
    - score_regime: ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（マクロキーワードリスト）・LLM 呼び出し・合成ロジック・閾値判定を実装。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - _MODEL やリトライ挙動を定数で管理、テスト用に _call_openai_api をモジュール内で独立実装。
- ロギング・堅牢性
  - 各処理でログ出力（INFO/WARNING/DEBUG/EXCEPTION）を充実させ、DB 書込時は BEGIN/DELETE/INSERT/COMMIT の冪等パターン、例外時は ROLLBACK を試みる実装。
  - DuckDB の executemany に関する互換性（空リスト回避）を考慮した実装。
- その他
  - モジュール設計上、datetime.today()/date.today() を直接参照しない方針を徹底（ルックアヘッドバイアス防止）。
  - 外部 API 呼び出し失敗時のフェイルセーフ（ゼロフォールバックやスキップ）により ETL / スコア処理の耐障害性を確保。

### Changed
- 新規リリースのため該当なし。

### Fixed
- 新規リリースのため該当なし。

### Removed
- 新規リリースのため該当なし。

### Security
- 環境変数の上書き制御:
  - .env ロード時に既存 OS 環境変数を protected として保護する挙動を実装。必要に応じ .env.local で上書き可能だが、テストや CI 用に自動ロードは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注記:
- この CHANGELOG はコードベース（src/kabusys 以下）の実装内容から推測して作成しています。実際のリリースノート作成時はリリース履歴・開発履歴に基づき調整してください。