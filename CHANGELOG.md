# Changelog

すべての注目すべき変更履歴はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。<https://keepachangelog.com/ja/1.0.0/>

注: この CHANGELOG はリポジトリの現行コードベース（version 0.1.0）から推測して作成しています。

## [Unreleased]

(現在差分なし)

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージルート: src/kabusys/__init__.py にてバージョンと公開モジュールを定義。
- 環境設定 / ローダー (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索、CWD に依存しない）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーは export 形式、クォート、エスケープ、インラインコメント等に対応。
  - OS 環境変数を保護する protected オプション（.env 読み込みで上書きを制御）。
  - Settings クラスを公開（J-Quants / kabuステーション / Slack / DB パス / 環境モード / ログレベル等のプロパティとバリデーションを提供）。
  - 環境値検証: KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装。
- AI モジュール (kabusys.ai)
  - ニュース NLP (news_nlp)
    - OpenAI（gpt-4o-mini）を用いたニュース記事の銘柄別センチメント解析。
    - スコアリングウィンドウ（JST: 前日 15:00 ～ 当日 08:30）の算出ユーティリティ（calc_news_window）。
    - 銘柄ごとに最新記事を集約し、1チャンク最大20銘柄でバッチ送信。
    - 1銘柄あたりの記事数・文字数上限（記事数: 10、文字数: 3000）によるトリム。
    - JSON mode を使用したレスポンスバリデーション（results リスト、code/score の検証、スコアを ±1.0 にクリップ）。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライの実装。
    - 部分失敗時に既存の他銘柄スコアを保持するため、書き込みは取得済みコードのみ DELETE → INSERT で置換（DuckDB 対応のため executemany を使用し、空リスト処理に注意）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定 (regime_detector)
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - マクロキーワードで raw_news をフィルタリングし、最大 20 記事を LLM に送信。
    - LLM 呼び出しは gpt-4o-mini（JSON mode）、API 呼び出し失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 計算結果は冪等に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - ルックアヘッドバイアス対策として datetime.today()/date.today() を直接参照せず、データベースクエリは target_date 未満条件等で安全性を確保。
- データ ETL / パイプライン (kabusys.data.pipeline / etl)
  - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー一覧を保持）。
  - 差分更新・バックフィル（デフォルト backfill 期間）・品質チェック・jquants_client 経由の保存を想定した設計。
  - DuckDB のテーブル存在チェック・最大日付取得などのユーティリティを提供。
- 市場カレンダー管理 (kabusys.data.calendar_management)
  - market_calendar テーブルを利用した営業日判定ロジックを実装:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
  - DB 登録値優先、未登録日は曜日ベースのフォールバック（週末除外）を行う一貫した挙動。
  - calendar_update_job を実装: J-Quants API から差分取得して market_calendar を冪等に更新。バックフィル、健全性チェック (_SANITY_MAX_FUTURE_DAYS) を内蔵。
  - 最大探索日数制限（_MAX_SEARCH_DAYS）により無限ループを回避。
- リサーチ / ファクター群 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M）、200日 MA 乖離、ATR/流動性/出来高指標、バリュー（PER, ROE）等の計算関数を実装（DuckDB SQL を中心に実装）。
    - データ不足時の扱い（不足で None を返す等）。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、horizons パラメータにより制御）、IC（スピアマンランク相関）算出、ランク変換ユーティリティ、ファクター統計サマリーを実装。
    - 外部依存（pandas 等）を用いずに標準ライブラリのみで実装。
- 共通設計方針（パッケージ全体）
  - Look-ahead バイアス防止のため、日付計算は全て外部から渡された target_date を基準に処理。
  - DB 書き込みは可能な限り冪等化（DELETE → INSERT / ON CONFLICT 相当）を採用。
  - OpenAI 呼び出しについては JSON mode を活用し、レスポンス検証とフォールバック戦略を実装。
  - テスト容易性を意識した設計（API 呼び出し箇所の patch 可能化、環境ロードを無効化するフラグ等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY を通じて注入する設計。環境変数が未設定の場合は ValueError を発生させる箇所があるため、運用時はキー管理に注意。

### Notes / 注意事項
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など（Settings クラスのプロパティ参照）。
- DuckDB 固有の取り扱い:
  - executemany に空リストを渡すとエラーになるバージョン（例: DuckDB 0.10）を想定してガードを追加。
- OpenAI 呼び出し:
  - モデルは gpt-4o-mini を指定。JSON mode を使用するため、レスポンスのバリデーションを必ず行うこと。
  - API の一時的失敗は指数バックオフでリトライし、最終的に失敗した場合は影響範囲を局所化して継続する（例: macro_sentiment=0.0 で継続、ニューススコアは未取得分スキップ）。
- DB トランザクション:
  - 明示的な BEGIN / DELETE / INSERT / COMMIT を採用し、失敗時は ROLLBACK を試行する実装。ROLLBACK 自体が失敗した場合は警告ログを出力して上位へ例外を伝播。
- テスト支援:
  - AI 呼び出し箇所（_kabusys.ai.*._call_openai_api）を patch してユニットテスト可能。

---

今後のリリースでは、モジュール間のドキュメント整備、追加の監視・実行コンポーネント（__all__ に示された execution, monitoring 等）の実装、CI 用のテストカバレッジ向上、外部 API クライアント（kabuステーション、J-Quants）の詳細実装とエラーハンドリング強化が想定されます。