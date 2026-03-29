# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。  
リリースポリシー: SemVer 準拠（このリポジトリは現時点で v0.1.0 を公開しています）。

※ 内容はコードベースから推測して作成しています。

## [Unreleased]
- (無し)

## [0.1.0] - 2026-03-29
Initial release — 日本株自動売買／データ基盤およびリサーチ用ユーティリティ群を提供。

### Added
- パッケージ基礎
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ でエクスポート。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
  - .env パーサは以下をサポート:
    - export KEY=val 形式
    - シングル/ダブルクォート付き値（バックスラッシュエスケープ対応）
    - 行内コメント判定（クォート無しの '#' は直前が空白/タブの場合にコメントとして扱う）
  - Settings クラスによりアプリ設定をプロパティ化:
    - J-Quants、kabuステーション、Slack、DBパス（duckdb/sqlite）、実行環境（development/paper_trading/live）、ログレベル判定など。
  - 必須環境変数未設定時は ValueError を送出するヘルパーを提供。

- AI 関連 (kabusys.ai)
  - news_nlp モジュール:
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へ渡し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む。
    - バッチ処理 (最大 20 銘柄/回)、トークン肥大対策（記事数上限・文字数トリム）を実装。
    - JSON Mode を用いた厳密なレスポンス検証、レスポンスパースの復元（余分な前後テキストから最外の {} を抽出）を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフ・リトライを実装。重大な失敗でも処理を続行し、フェイルセーフ（部分書き込み保護）を採用。
    - DuckDB の executemany 空リスト制約に配慮し、書き込み前に空チェックを行う。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込み。
    - マクロニュースは news_nlp の時間ウィンドウ計算を利用（calc_news_window）して抽出。
    - API 呼び出しはリトライ/バックオフを行い、最終的に失敗した場合は macro_sentiment = 0.0 として継続（フェイルセーフ）。
    - OpenAI 呼び出しはテストで差し替え可能な設計（別モジュールとプライベート関数を共有しない）。

- データ処理・ETL (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理用ユーティリティを実装（market_calendar テーブル参照）。
    - 営業日判定: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB にデータが無い場合は曜日ベース（平日のみ営業日）でフォールバックする一貫したロジックを採用。
    - calendar_update_job: J-Quants から差分取得して冪等保存（バックフィル、健全性チェックあり）。
  - pipeline (ETL):
    - ETLResult dataclass を導入し ETL 実行結果（取得数、保存数、品質問題、エラー）を集約。
    - 差分更新・バックフィル戦略、品質チェック統合（quality モジュール）に対応。
    - DuckDB の挙動（executemany の空リスト不可など）を考慮した堅牢な書き込み手順を実装。

- Research (kabusys.research)
  - factor_research:
    - モメンタム (1M/3M/6M)、200日MA乖離、ATR（20日）、平均売買代金、出来高比率、PER/ROE（raw_financials から）などのファクター計算関数を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用した実装で、結果は (date, code) をキーとする dict のリストで返却。
  - feature_exploration:
    - 将来リターン計算 (calc_forward_returns)、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を提供。
    - Spearman（ランク相関）を自前実装で算出（ties は平均ランク）。
    - pandas 等外部依存を避け、標準ライブラリのみで実装。

- テスト性・堅牢性
  - OpenAI 呼び出しを内部関数として抽象化し、ユニットテスト用に patch で置き換え可能にしている。
  - 各種操作で BEGIN/DELETE/INSERT/COMMIT の冪等パターンを採用し、書き込み失敗時は ROLLBACK を試みて上位へ例外を伝播。
  - データ不足や API エラー時には明示的なログ出力と安全なフォールバックを行う設計（例: ma200_ratio=1.0、macro_sentiment=0.0、スコア取得失敗はスキップ等）。

### Changed
- (初回リリースのため該当なし)

### Fixed
- (初回リリースのため該当なし)

### Deprecated
- (初回リリースのため該当なし)

### Removed
- (初回リリースのため該当なし)

### Security
- OpenAI API キーや各種トークン（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN など）は環境変数で渡すことを前提としており、未設定時は明確に例外を発生させる（誤った無視を避けるため）。
- .env 自動読み込みはデフォルトで有効だが、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能。

---

## 互換性・注意点 / Migration notes
- OpenAI 依存:
  - score_news / score_regime は OpenAI API（gpt-4o-mini）を使用します。api_key 引数を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。未設定の場合は ValueError を送出します。
  - LLM 呼び出し失敗時の挙動: 通常はフェイルセーフ（ゼロスコアやスキップ）で継続しますが、DB 書き込み失敗など一部は例外を伝播します。

- DuckDB 側の注意:
  - executemany に空リストを渡すとエラーになる DuckDB（0.10 等）に対応するため、空チェックを行っています。
  - 日付カラムの型は日付（date）で扱うことを想定しています。DB からの型が文字列の場合は date.fromisoformat で変換します。

- 時刻・タイムゾーン:
  - news_nlp のウィンドウ計算は JST を基準にし、DB と比較する際は UTC naive datetime を使用しています（コメントに詳細あり）。タイムゾーン混在に注意してください。
  - 多くの関数はルックアヘッドバイアスを避けるため datetime.today() を参照しないよう設計されています（ただし calendar_update_job は date.today() を使用：夜間バッチ想定）。

- 想定される DB スキーマ（主なテーブル）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials, 等。初回導入時は ETL を通してデータを投入してください。

---

## 今後の改善候補（コードから推測）
- OpenAI 呼び出しのモデルやタイムアウト等を設定可能にする（現在は定数化）。
- news_nlp / regime_detector の並列化やレート管理の高度化（現在はチャンク単位直列処理）。
- calendar_update_job の time zone や実行日時の柔軟化（現在は date.today() ベース）。
- より厳格なレスポンススキーマ検証や異常時の監視（現在はログ出力＋フェイルセーフ）。

---

作成者注: 上記はリポジトリ内のソースコードから機能・設計方針を推測して作成した CHANGELOG です。実際の変更履歴（コミットメッセージやリリースノート）と差異がある可能性があります。