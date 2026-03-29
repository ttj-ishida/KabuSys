# CHANGELOG

このプロジェクトでは Keep a Changelog の形式に従い、重要な変更を記録します。  
全ての利用者が変更の影響を理解できるよう、機能追加・修正・設計方針などを日本語でまとめています。

全般的な注記:
- 本リリースはパッケージ初期バージョン相当のまとまった機能実装を含みます。
- DuckDB を内部データベースとして用いる設計、外部 API（J-Quants、OpenAI）との連携、ならびに自動環境変数読み込みなどの仕組みを提供します。
- 設計方針として「ルックアヘッドバイアス防止」「冪等性（idempotency）」「外部API障害時のフェイルセーフ」を重視しています。

## [0.1.0] - 2026-03-29

### Added
- 基本パッケージ構成を追加
  - kabusys パッケージの公開 API を定義（data, strategy, execution, monitoring を __all__ に設定）。
  - パッケージバージョンを `0.1.0` に設定。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの探索は __file__ を起点に `.git` または `pyproject.toml` を探す方式で実装（CWD に依存しない）。
    - 優先順位: OS環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動読み込み無効化をサポート（テスト用途想定）。
  - .env のパースを強化:
    - コメント行、`export KEY=val` 形式、シングル/ダブルクォートとエスケープ対応、インラインコメント判定ロジックを実装。
    - 上書き（override）・保護キー（protected）を考慮した読み込み。
  - Settings クラスを提供し、主要設定（J-Quants、kabu API、Slack、DBパス、実行環境、ログレベル等）をプロパティで取得。
    - 必須設定未定義時には明確な ValueError を送出。

- AI 関連機能（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄別センチメント（ai_score）を算出、ai_scores テーブルへ書き込み。
    - タイムウィンドウの計算（JST基準）と窓の変換ユーティリティを実装（calc_news_window）。
    - バッチ処理（最大 20 銘柄/コール）、記事数や文字数のトリム、レスポンスの厳格なバリデーションを実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ・リトライを実装。API失敗時はスキップして処理継続（フェイルセーフ）。
    - レスポンスの JSON 抽出/復元ロジックを追加し、部分的な余計なテキスト混入にも耐性を持たせる。
    - DuckDB への書き込みは冪等性を意識（対象コードのみ DELETE → INSERT）し、部分失敗時に既存データを保護する。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ保存する処理を実装。
    - マクロニュース抽出のキーワードセット、LLM へのプロンプト（厳密JSON出力要求）、OpenAI 呼び出しのリトライ/フェイルセーフ挙動を実装。
    - DuckDB クエリはルックアヘッドを防止する条件（date < target_date 等）を厳守。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等フローを採用し、失敗時には ROLLBACK を試行。

- データ処理（kabusys.data）
  - ETL 基盤（kabusys.data.pipeline）
    - ETL の結果を表現する dataclass ETLResult を実装し、外部にエクスポート（kabusys.data.etl）。
    - 差分取得、バックフィル、品質チェックのためのユーティリティとヘルパー関数を実装（テーブル存在確認、最大日付取得など）。
    - ETL の設計方針: 最終取得日に基づく差分取得、backfill による後出し修正吸収、品質チェックは収集して呼び出し元で判断する方式。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）に基づく営業日判定・Next/Prev 営業日検索・期間内営業日取得・SQ日判定を実装。
    - market_calendar が未取得な場合は曜日ベースのフォールバック（週末を休業日扱い）を行い、一貫性を保つ設計。
    - カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装し、J-Quants からの差分取得→保存（冪等）を行う。バックフィル・健全性チェックを実装。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR、相対ATR、出来高関連）、Value（PER/ROE）を DuckDB の SQL / Python 組合せで実装。
    - データ不足時は None を返す等の堅牢な設計。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ランク関数、ファクター統計サマリーを実装。
    - pandas 等に依存しない純標準ライブラリ実装、欠損・非有限値の扱いに配慮。

### Changed
- ロギング・エラーハンドリングを明確化
  - API 失敗やデータ不足時に警告・情報ログを出すことで障害の原因追跡を容易に。
  - DuckDB 書き込み失敗時は ROLLBACK を試行し、二次エラー時は警告ログを出力。

- 安全性・堅牢性を重視したデフォルト挙動
  - AI 呼び出しの失敗や不正レスポンスに対しては例外を投げずフォールバック値（例: 0.0）を用いる箇所を設け、パイプライン全体の停止を防止。

### Fixed
- .env パースの微妙なケース（クォート内のエスケープ、インラインコメントの誤認）に対する取りこぼしを修正（より正確な抽出を実装）。
- DuckDB executemany の空リストバインドに対する互換性対策（空の場合は呼び出さないガードを追加）。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI / 外部 API キーは Settings により環境変数で管理する設計。APIキー未設定時は明確な ValueError を送出して誤使用を防止。

---

注: この CHANGELOG は現行ソースコードの実装内容を基に推測して作成しています。実際のリリースノート作成時は、開発履歴（コミットログ）やリリースに関わる追加情報（互換性の注意点、マイグレーション手順等）を合わせて追記してください。