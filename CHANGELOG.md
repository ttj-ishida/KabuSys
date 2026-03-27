# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-27
初回公開リリース。

### Added
- パッケージの骨組みを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定管理
  - .env ファイルと OS 環境変数を統合して読み込む自動ロード機能を実装（src/kabusys/config.py）。
  - .env のパースで以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - 行内コメントの取り扱い（クォート外・直前スペースありの # をコメントとして認識）
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数必須チェック用の _require() と Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID などのプロパティ含む）。
  - env / log_level 等のバリデーション（許容値チェック）と is_live / is_paper / is_dev 判定。

- データ関連（DuckDB ベース）
  - ETL 結果を表す ETLResult 型（src/kabusys/data/pipeline.py）を公開（src/kabusys/data/etl.py 経由で再エクスポート）。
  - ETL パイプラインの基礎実装（差分取得、バックフィル、品質チェックフック、DuckDB の最終日取得ユーティリティ等）。
  - マーケットカレンダー管理モジュール（src/kabusys/data/calendar_management.py）：
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定 API。
    - calendar_update_job による J-Quants からの夜間差分取得・冪等保存処理。
    - DB 未取得時の曜日ベースのフォールバックと健全性チェック実装。

- 研究（Research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）
    - ボラティリティ / 流動性（20日 ATR、20日平均売買代金、出来高比等）
    - バリュー（PER、ROE の取得）
    - DuckDB 上で SQL と Python の組合せで計算する設計
  - 特徴量探索（src/kabusys/research/feature_exploration.py）:
    - 将来リターン計算（任意ホライズン）
    - IC（Spearman rank）計算
    - ランク変換ユーティリティ（同順位は平均ランク）
    - ファクターの統計サマリー（count/mean/std/min/max/median）
  - 既存ユーティリティの再エクスポート（zscore_normalize など）。

- AI / NLP
  - ニュース NLP（src/kabusys/ai/news_nlp.py）:
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）へ JSON Mode でバッチ送信して銘柄ごとにセンチメントを算出、ai_scores に書き込む機能。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）と記事トリム（記事数上限・文字数上限）の実装。
    - バッチサイズ、リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ、レスポンスバリデーション、スコアのクリップ処理。
    - DuckDB の executemany 空リスト問題を回避する安全処理。
    - テスト容易性のため _call_openai_api を patch 可能に実装。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）:
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日 MA 乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次で 'bull'/'neutral'/'bear' を判定し market_regime テーブルに書き込む。
    - マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）による JSON 応答パース、リトライ・フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス回避に配慮（date 引数ベース、today を直接参照しない）。
    - テスト用に _call_openai_api を差し替え可能。

- モジュール公開整理
  - ai パッケージで score_news を公開（src/kabusys/ai/__init__.py）。
  - research パッケージで各計算関数を公開（src/kabusys/research/__init__.py）。

### Fixed / Defensive behaviors
- DB 書き込み時の冪等性を考慮した処理を多くの箇所で採用（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK の使用）。
- OpenAI レスポンスの JSON 変動（前後余計テキスト混入など）に対する復元ロジックを実装して耐性を確保。
- API エラー種別に応じたリトライ策略（RateLimit/接続/タイムアウト・5xx など）と、リトライ失敗時のフェイルセーフ（ゼロフォールバックやスキップ）を実装。
- DuckDB の型や返却値に対する堅牢な変換（date 系、NULL 値取り扱い、executemany の空配列回避）。
- カレンダー未取得時のフォールバックや、market_calendar に NULL が混入した場合の警告とフォールバック処理を追加。

### Security
- .env 読み込み時に OS 環境変数を保護する仕組み（protected セット）を導入し、override 動作でも OS 環境変数を上書きしないように実装。
- 重要な外部 API キー（OpenAI・Slack・kabu API・J-Quants）を Settings の必須プロパティとして明示し、未設定時に早期エラーを発生させることで誤動作を防止。

### Notes / Implementation details
- OpenAI モデルはデフォルトで "gpt-4o-mini" を使用。
- ニュース関連は「JSON Mode」での応答を前提に設計しているが、実運用での差異に備えたパース耐性を持つ。
- ルックアヘッドバイアス対策として、全ての「日付を基準とする」計算は target_date 引数を受け取り、内部で datetime.today() / date.today() を直接参照しない方針を徹底。
- DuckDB を主要なローカル分析 DB として想定しており、互換性のため一部 SQL の書き方や executemany の扱いに注意を払っている。

（以上）