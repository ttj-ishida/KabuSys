# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従います。  
このプロジェクトでは、API の安定性・再現性・フォールトトレランスを重視して設計されています。

---

## [Unreleased]

（現在なし）

---

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な追加点をモジュール別にまとめます。

### Added

- パッケージ基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。
  - パッケージ公開 API: `data`, `strategy`, `execution`, `monitoring` を __all__ に設定。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読込する仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に自動探索（カレントディレクトリに依存しない）。
  - .env パーサを実装（kabusys.config._parse_env_line）
    - コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを適切に処理。
  - 環境変数読み込みの安全性
    - `.env` 読み込み時に既存 OS 環境変数を保護する `protected` 機構。
    - ロード失敗時は警告を出力。
  - Settings クラスを実装（kabusys.config.Settings）
    - J-Quants / kabuステーション / Slack / DB パスなど主要設定をプロパティで公開。
    - 必須値未設定時は明確な ValueError を発生させる `_require` 実装。
    - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーション（許容値を限定）。
    - ユーティリティプロパティ: `is_live`, `is_paper`, `is_dev`。

- AI 関連（kabusys.ai）
  - ニュースセンチメント解析（kabusys.ai.news_nlp.score_news）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）に JSON モードで送信して銘柄ごとのセンチメントを算出。
    - ウィンドウ定義（JST）: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリで扱う）。
    - バッチ処理: 最大 20 銘柄/API コール。1 銘柄当たり記事数・文字数上限でトリム（既定: 10 件 / 3000 文字）。
    - 再試行（リトライ）: 429、ネットワーク断、タイムアウト、5xx に対する指数バックオフ（最大試行回数制御）。
    - レスポンス検証: JSON 抽出、`results` リスト構造検証、コード照合、数値検証、±1.0 でクリッピング。
    - DB 書き込みは idempotent に実施（対象コードのみ DELETE → INSERT、トランザクション）。
    - API キーは引数で注入可能。未指定時は環境変数 `OPENAI_API_KEY` を参照。
    - フェイルセーフ: API エラー時は該当チャンクをスキップし他コードに影響を与えない（例外を全面送出しない）。
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
    - ETF 1321（Nikkei225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算、マクロキーワードでフィルタしたニュース抽出、OpenAI での macro_sentiment 評価、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - OpenAI 呼び出しは独立実装、再試行ロジックとフェイルセーフ（API 失敗時は macro_sentiment = 0.0）を備える。
    - API キー注入可能（引数 / 環境変数）。

- データ / ETL（kabusys.data）
  - ETL 結果データクラス（kabusys.data.pipeline.ETLResult）を公開（kabusys.data.etl で再エクスポート）。
    - ETL の取得件数・保存件数・品質チェック結果・エラー履歴などを集約。ユーティリティ to_dict を提供。
  - ETL パイプラインユーティリティ（kabusys.data.pipeline）
    - 差分更新、バックフィル、品質チェック連携のための共通ロジックを実装（内部ユーティリティ関数を含む）。
    - DuckDB 上での最終日付取得、テーブル存在チェック等を実装。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間更新ジョブ（calendar_update_job）を実装。
      - J-Quants クライアント経由で差分取得し、冪等保存（ON CONFLICT / 上書き相当）を行う。
      - バックフィル（直近数日再取得）と健全性チェック（未来日チェック）を実装。
    - 営業日判定ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - カレンダー未取得時は曜日ベース（平日のみ営業日）でフォールバックする一貫した挙動を採用。
    - 探索上限日数を設定し無限ループを防止。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - calc_value: PER（EPS が 0/欠損なら None）、ROE（raw_financials と prices_daily を結合して算出）。
    - いずれも DuckDB の SQL ウィンドウ関数を活用し、データ不足の場合は None を返す設計。
  - 特徴量探索・統計（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定日の終値から将来リターン（任意の horizon）を LEAD で一括取得。horizons の妥当性チェックあり。
    - calc_ic: スピアマン（ランク）相関（Information Coefficient）を実装。十分なサンプルがない場合 None を返す。
    - rank: 同順位は平均ランクで処理（浮動小数丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー機能。
  - 研究モジュール公開 API を整理（__all__）。

- その他
  - モジュールの公開 API を整備（ai/__init__.py, research/__init__.py, data/etl 再エクスポート 等）。
  - DuckDB を主要ストレージとして使用する設計を統一。
  - 日付取り扱いにおけるルックアヘッドバイアス防止方針を徹底（datetime.today()/date.today() を計算ロジック内部で参照しない点をドキュメント化・実装）。

### Changed

- （初版リリースのため該当なし）

### Fixed

- （初版リリースのため該当なし）

### Deprecated

- （初版リリースのため該当なし）

### Removed

- （初版リリースのため該当なし）

### Security

- （初版リリースのため該当なし）

---

Notes / 備考
- OpenAI API を利用する機能（news_nlp, regime_detector）は API キーの管理に注意してください。デフォルトで環境変数 `OPENAI_API_KEY` を利用しますが、関数引数でキー注入が可能です（テスト容易性向上）。
- .env 読み込みの自動化は便利ですが、テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを抑止することを推奨します。
- DuckDB のバージョン差異に起因する挙動（例: executemany に空リストが使えない等）を考慮した実装が行われています。
- 初期リリースのため一部機能（例: PBR・配当利回り等のバリューファクター）は未実装。将来的な拡張を想定しています。

---

作者: kabusys 開発チーム