# Changelog

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog に従い、セマンティック バージョニングを使用します。

※ 本 CHANGELOG は現行コードベースの内容から推測して作成しています。

## [Unreleased]

---

## [0.1.0] - 2026-03-29

初回リリース。以下の主要機能とモジュールを実装・公開しました。

### 追加 (Added)
- パッケージ基本
  - パッケージ名 kabusys を導入。公開バージョン __version__ = 0.1.0。
  - パッケージの公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 設定管理 (kabusys.config)
  - .env / .env.local ファイルと環境変数から設定を読み込む自動読み込み実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を起点にルートを特定（CWD 非依存）。
  - .env パーサ: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、行内コメント処理などを考慮した堅牢なパーサ実装。
  - 自動読み込みの抑止フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト時に無効化可能）。
  - 環境変数必須チェック用の _require と Settings クラスを実装。J-Quants / kabu / Slack / DB パス等の設定プロパティを提供。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）を実装。
  - デフォルトの DB パス（DuckDB / SQLite）の展開（expanduser）を実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols から銘柄ごとに記事を集約して OpenAI API（gpt-4o-mini）にバッチ送信し、ai_scores テーブルにスコアを書き込む処理を実装。
    - タイムウィンドウ計算（JST ベース）と UTC 変換を実装（calc_news_window）。
    - バッチサイズ制御、記事数・文字数のトリミング（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - JSON Mode を想定した堅牢なレスポンス検証 (_validate_and_extract)。前後の余計なテキスト混入時の復元処理も実装。
    - レート制限（429）・ネットワーク断・タイムアウト・5xx のエクスポネンシャルバックオフによるリトライ実装。失敗時はスキップして継続するフェイルセーフ設計。
    - DuckDB への置換的書き込み（DELETE → INSERT）を実装し、部分失敗時に既存のスコアを保護。
    - テスト用フック: OpenAI 呼び出し関数を patch で差し替え可能（_call_openai_api）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する機能を実装。
    - prices_daily/raw_news からデータを取得、OpenAI（gpt-4o-mini）を用いたマクロセンチメントスコア算出（_score_macro）。
    - API 呼び出しのリトライ戦略、エラー時のフォールバック（macro_sentiment=0.0）を実装。
    - 計算結果を market_regime テーブルへ冪等に書き込むトランザクション処理（BEGIN/DELETE/INSERT/COMMIT）と ROLLBACK の安全処理。
    - ルックアヘッドバイアス対策（date < target_date 等で過去データのみ使用）を設計方針に明示。

- データ関連 (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を参照する営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫性ある振る舞いを実装。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants から差分取得 → 保存）。バックフィルと健全性チェック（将来日付の異常検出）を実装。
  - ETL パイプライン関連 (kabusys.data.pipeline, kabusys.data.etl)
    - ETL の処理設計に基づく差分取得 / 保存 / 品質チェックフレームワークを実装。
    - ETLResult データクラスを提供（ターゲット日、取得数・保存数、品質問題リスト、エラーリスト等）。to_dict メソッドで品質問題をシリアライズ可能。
    - テーブル存在チェックや最大日付取得等のユーティリティを実装。
    - jquants_client と quality モジュールと連携する設計（クライアント注入でテスト容易性確保）。
  - data パッケージのインターフェース整備（ETLResult の再エクスポート等）。

- リサーチ/ファクター (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金 / 出来高比）およびバリュー（PER, ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用した実装、データ不足時の None 扱い等の堅牢な挙動。
    - 設計上、本コードは prices_daily/raw_financials のみ参照し、外部の発注 API には接触しない。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）のリターンを LEAD を用いて一度のクエリで算出。
    - IC（Information Coefficient）計算（calc_ic）: Spearman（ランク相関）を生の Python で実装。データ不足や ties の扱いに配慮。
    - ランク変換ユーティリティ（rank）および基本統計サマリー（factor_summary）を実装。
    - 外部依存を避け標準ライブラリのみでの実装。

### 変更 (Changed)
- （初回リリースのため履歴は追加が中心。実装上の設計選択やデフォルト値を文書化）
  - OpenAI 呼び出しは gpt-4o-mini をデフォルトモデルとして採用し、JSON Mode を利用する設計に統一。
  - DuckDB との相互作用において、executemany による空リストバインド制限（DuckDB 0.10 の挙動）を考慮した処理を導入（空のときは実行をスキップ）。
  - すべての時刻/日付操作は明示的に date/datetime を操作し、datetime.today()/date.today() の無制限参照を避ける方針を採用（ルックアヘッドバイアス回避）。

### 修正 (Fixed)
- OpenAI の API エラー分類に応じたリトライ / 非リトライの振る舞いを明確化。5xx 系はリトライ、4xx（致命的なエラー）は即スキップするフェイルセーフ実装。
- JSON パース失敗時の復元ロジックを追加し、LLM の出力フォーマット揺らぎ（前後テキスト混入）に対処。

### セキュリティと運用 (Security / Ops)
- 環境変数読み込みにおいて、既存 OS 環境変数を protected として上書き防止する仕組みを導入。明示的に .env.local で override 可能。
- 必須キーが未設定の場合は早期に ValueError を投げることで運用ミスを検出。

### テスト支援 (Testing)
- OpenAI 呼び出し箇所に差し替え可能な内部関数（_call_openai_api）を用意。unittest.mock.patch によるモックが容易。

---

開発中の機能・TODO（コードからの推測）
- strategy / execution / monitoring の具体的実装はパッケージ公開のためにエクスポートされているが、本差分では内部処理の詳細が示されていないため、今後の実装で自動売買ロジック・発注エンジン・モニタリング機能が追加される想定。
- jquants_client / quality 等外部モジュールとの統合テストおよび例外処理の強化。

---

参考: 主要ファイル一覧（実装済み）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/ai/regime_detector.py
- src/kabusys/research/factor_research.py
- src/kabusys/research/feature_exploration.py
- src/kabusys/research/__init__.py
- src/kabusys/data/calendar_management.py
- src/kabusys/data/pipeline.py
- src/kabusys/data/etl.py

（以上）