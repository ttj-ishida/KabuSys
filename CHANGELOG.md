Keep a Changelog の形式に準拠した CHANGELOG.md（日本語）を作成しました。コードベースから推測できる追加機能、設計方針、重要な実装上の注意点を反映しています。

----
Keep a Changelog
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
- なし

[0.1.0] - 2026-03-31
Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、__version__ = 0.1.0
  - パブリックAPIエクスポート: data, strategy, execution, monitoring（__all__ に宣言）

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数を自動読み込み（優先順: OS環境変数 > .env.local > .env）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - コメント（#）の解釈ルール（クォート外かつ直前がスペース／タブの場合をコメント扱い）
  - 読み込み時の上書き制御（override, protected）を導入してOS環境変数を保護
  - Settings クラスを提供（環境変数をプロパティとして取得）
    - J-Quants、kabuステーション、Slack、データベースパス、監視閾値、環境種別（development/paper_trading/live）、
      ログレベル（DEBUG/INFO/...）等のプロパティ
    - 必須変数未設定時は ValueError を送出
    - env/log_level の値検証を実装
    - Path 型を返すプロパティ（expanduser を適用）

- AI モジュール（kabusys.ai）
  - news_nlp モジュール（ニュースセンチメント）
    - ニュース集計ウィンドウ計算（JST -> UTC 変換）と記事集約ロジック
    - 銘柄ごとに記事を集約し、1銘柄あたりの文字数・記事数をトリム（_MAX_CHARS_PER_STOCK, _MAX_ARTICLES_PER_STOCK）
    - OpenAI（gpt-4o-mini）を JSON モードで呼び出し、最大 _BATCH_SIZE 銘柄をまとめて送信
    - リトライ戦略: 429/ネットワーク/タイムアウト/5xx に対して指数バックオフで再試行
    - レスポンスのバリデーション実装（JSON復元ロジック、results 配列検査、コード/スコア検証）
    - スコアを ±1.0 にクリップ
    - 書き込みは冪等（該当 date/code の DELETE → INSERT）で部分失敗時に既存スコアを保護
    - テストしやすさのため _call_openai_api を切り替え可能に設計
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計

  - regime_detector モジュール（市場レジーム判定）
    - ETF 1321（日経225連動）の 200 日移動平均乖離と、マクロニュース（LLMセンチメント）を重み合成して
      日次で市場レジーム（bull/neutral/bear）を判定
    - マクロ記事はキーワードでフィルタ（_MACRO_KEYWORDS）、最大 _MAX_MACRO_ARTICLES 件を取得
    - LLM 呼び出しは gpt-4o-mini を使用、JSON レスポンスを期待
    - リトライ戦略・エラーハンドリング（API 関連の失敗時は macro_sentiment=0.0 で継続）
    - 最終結果は market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - テストのために OpenAI 呼び出し部分を外部差替えしやすい構成

- Data モジュール（kabusys.data）
  - calendar_management（市場カレンダー管理）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の提供
    - market_calendar がない場合は曜日日ベース（土日非営業）でフォールバック
    - DB 登録データ優先、未登録日は曜日フォールバックで一貫した挙動
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、健全性チェック含む）
    - 最大探索日数制限やバックフィル、異常検出時のスキップなどの安全策を実装

  - pipeline / etl（ETL）・ETLResult クラス
    - ETLResult データクラスによる ETL 実行結果の構造化（取得件数、保存件数、品質問題、エラー一覧等）
    - ETL パイプライン方針: 差分更新、idempotent 保存、品質チェック（quality モジュール）に基づく実装方針を定義
    - DuckDB 連携を前提としたユーティリティ関数（テーブル存在確認、最大日付取得など）
    - DuckDB 0.10 に対する互換性考慮（executemany に空リストを渡さない等）

- Research モジュール（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）等の計算関数を実装
    - DuckDB 内で SQL とウィンドウ関数を用いて計算
    - データ不足時の None 戻り、ログ出力
  - feature_exploration
    - calc_forward_returns（将来リターン）、calc_ic（Spearman ランク相関 / IC）、rank、factor_summary（統計サマリ）等を実装
    - 外部ライブラリに依存せず純粋な Python / SQL で実装
    - rank は同順位を平均ランクで処理（丸めにより ties 検出の安定化）

Changed
- 設計原則の明文化（実装内 docstring）
  - ルックアヘッドバイアス防止のため日付参照を外部から注入する設計（date.today() を直接参照しない）
  - OpenAI 呼び出しや外部API呼び出しはフォールバック（失敗時に処理継続）を採用して堅牢性を確保
  - DB 書き込みは冪等性を保証する（部分失敗時に既存データを不要に消さない）

Fixed / Robustness improvements
- .env パースの堅牢化（クォート内エスケープやコメント処理の改善）
- OpenAI レスポンスパース失敗時に致命的に止めないフォールバック実装（ログ出力して 0.0 またはスキップ）
- JSON mode でも前後に余計なテキストが混入する場合に最外の {} を抽出して復元する処理を追加
- DuckDB に対する executemany の空リスト回避（DuckDB 0.10 の制約に対応）
- DB トランザクションにおける例外時の ROLLBACK を安全に呼び出し、ROLLBACK 失敗時は警告ログを出す

Security
- 環境変数の必須チェックを導入（API キーや Slack トークンなど）。未設定時は ValueError を送出して明示的に通知
- OS 環境変数を保護するため .env 読み込み時に既存キーの上書き制御を実装

Notes / Operational
- 必須環境変数の例:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（OpenAI 用、関数呼び出し時に引数で注入可能）
- OpenAI 呼び出しは gpt-4o-mini を前提（response_format に JSON object を要求）
- データベース: デフォルトで DuckDB ファイル（data/kabusys.duckdb）や SQLite（data/monitoring.db）を参照するプロパティを設定
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に検索する（パッケージ配布後も CWD に依存しない実装）

BREAKING CHANGES
- 初版リリースのため互換性破壊は該当なし。

Acknowledgements / Implementation notes
- テスト容易性を考慮して内部の OpenAI 呼び出し関数（_kabusys.ai.*._call_openai_api）を patch/モック可能にしている
- 多くの処理で「失敗時に継続する（フェイルセーフ）」戦略を採用しており、監視や再実行（再試行）で補う設計になっている

----

この CHANGELOG はソースコードから推測して作成しています。必要であれば以下を追加できます:
- 各関数・メソッドの実装上の細かい変更履歴（コミット単位の差分に基づく詳細）
- 今後のリリース予定（マイルストーン）や未実装 TODO（例: PBR/配当利回りの追加、strategy/execution/monitoring の実装状況）