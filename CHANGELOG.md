# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このファイルはリポジトリのコードベースから推測して作成した初期リリース用の変更履歴です。

## [Unreleased]
- 今後の改善候補（実装済みコードから推測）
  - OpenAI 呼び出しの非同期化/並列化によるパフォーマンス改善
  - PBR / 配当利回りなどバリューファクターの追加実装
  - モニタリング・実行モジュール（execution / monitoring）の拡充
  - テストカバレッジ・例外ハンドリングの強化

---

## [0.1.0] - 2026-04-04 (初回リリース)
初期公開リリース。以下の主要機能とモジュールを追加。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは `0.1.0`。
  - __all__ で主要サブパッケージ（data, research, ai, ...）を公開する構成を採用。

- 環境設定 / config
  - .env ファイルと環境変数を読み込む自動ローダを実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - .env のパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理に対応）。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応（テスト等で使用可能）。
  - OS 環境変数の保護（既存キーを protected として上書きを制御）。
  - 必須環境変数チェック用の `_require` と Settings クラスを提供。設定項目のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）とデフォルト値（KABU_API_BASE_URL, DB パス等）を定義。
  - PID ファイル / キルフラグ / リソース閾値等の監視用設定項目を提供。

- AI：ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄単位のセンチメントを算出する `score_news` を実装。
  - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を行う `calc_news_window` を実装。
  - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの記事数上限・文字数トリム、レスポンス検証、スコアクリッピング（±1.0）を実装。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ・リトライを実装。
  - DuckDB への冪等書き込みロジック（DELETE → INSERT、executemany の空リスト回避）を実装。
  - テスト用に OpenAI 呼び出しの差し替えが可能なフック（_call_openai_api）を用意。

- AI：市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経連動）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出する `score_regime` を実装。
  - MA200 乖離計算、マクロキーワードによるニュース抽出、OpenAI 呼び出し（JSON mode）、リトライ・フォールバック（API失敗時 macro_sentiment=0.0）を実装。
  - 合成スコアの閾値判定と `market_regime` テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を提供。
  - OpenAI API キーの注入（引数 or 環境変数 OPENAI_API_KEY）をサポート。

- Research（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数群を実装。
    - DuckDB 上で SQL を中心に実装し、外部 API へはアクセスしない設計。
    - データ不足時の挙動（None 戻り）やログ出力に対応。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns：任意ホライズン対応）を実装。
    - IC（Information Coefficient）計算（スピアマン順位相関）とランク付けユーティリティを提供。
    - ファクター統計サマリ（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存しない純標準実装。

- Data（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーを前提に、営業日判定（is_trading_day）、翌営業日/前営業日取得、期間内営業日列挙、SQ 日判定などのユーティリティを追加。
    - market_calendar が未取得の場合は曜日ベース（平日のみ営業）でフォールバックする整合的ロジックを実装。
    - 夜間バッチの `calendar_update_job` を実装（J-Quants クライアント経由で差分取得、バックフィル・健全性チェックを実施）。
  - ETL パイプライン（pipeline）
    - ETL の結果を表す `ETLResult` データクラスを追加（品質チェック結果やエラー集約、辞書変換メソッドを提供）。
    - ETL の差分取得方針、バックフィルや品質チェックの方針を実装設計として反映。
  - etl.py で ETLResult を再エクスポート。

- 全体的な堅牢性
  - DB 書き込みで BEGIN/COMMIT/ROLLBACK を使った冪等保存とエラーハンドリング（ROLLBACK 失敗時の警告ログ）を採用。
  - OpenAI 呼び出しや外部 API に対してフェイルセーフ（失敗時はスコアを中立にする等）を実装し、処理継続性を重視。

### Changed
- （初回リリースのため該当無し）

### Fixed
- （初回リリースのため該当無し）

### Security
- 環境変数の取り扱いで OS 環境を保護する仕組みを導入（.env 上書き時に既存 OS 環境を protected として扱う）。
- OpenAI API キーは引数または環境変数から受け取る設計。未設定時は明示的な ValueError を発生させるため誤動作を防止。

### Deprecated
- （初回リリースのため該当無し）

### Removed
- （初回リリースのため該当無し）

### Notes / Known limitations
- AI 機能（score_news, score_regime）は OpenAI API（gpt-4o-mini, JSON mode）に依存。API キー未設定では動作しない。
- API 呼び出しは同期実装。大規模データでのスループット改善は今後の課題。
- バリューファクターの一部（PBR・配当利回り）は未実装（注記あり）。
- DuckDB のバージョン差異（executemany の空リスト扱い等）に対する実装上の注意があるため、デプロイ先の DuckDB バージョンでの動作確認を推奨。
- モジュールはテスト時に差し替え可能なフック（_call_openai_api 等）を備えているため、ユニットテストの作成が容易。

---

貢献やバグ報告、改善要望は Issue を通じて受け付けてください。