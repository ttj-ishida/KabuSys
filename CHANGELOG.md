# CHANGELOG

すべての注目すべき変更点はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

通常的なセクション:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連

## [Unreleased]

## [0.1.0] - 2026-04-01

初期リリース。日本株自動売買プラットフォームのコアライブラリを収録しています。主な機能・設計方針は以下の通りです。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージトップで主要サブパッケージを公開（data, strategy, execution, monitoring）。

- 環境・設定管理 (kabusys.config)
  - .env/.env.local 自動読み込み機能を実装（OS 環境変数を優先、.env.local は上書き）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を検索（CWD 非依存）。
  - 高機能な .env パーサを実装
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 環境変数の保護（読み込み時に既存 OS 環境変数を protected として上書きを制御）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得
    - 必須キーの検証（_require による ValueError 投げる挙動）
    - 各種デフォルト設定（KABUSYS_ENV, LOG_LEVEL, KABU_API_BASE_URL, DB パス等）
    - 環境変数値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL）
    - よく使う判定ヘルパー: is_live / is_paper / is_dev

- AI モジュール
  - ニュース NLP (kabusys.ai.news_nlp)
    - score_news: raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して ai_scores に書き込み
    - タイムウィンドウ計算（calc_news_window）: JST 基準で前日 15:00 ～ 当日 08:30 を UTC に変換して扱う（ルックアヘッドバイアス防止）
    - バッチ処理: 最大 20 銘柄／チャンク、1銘柄当たり最大記事数・文字数でトリム（トークン肥大化対策）
    - 再試行ロジック: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ
    - レスポンスの厳格なバリデーション（JSON 抽出・results 構造・スコア型検証）。不正応答はスキップして継続（フェイルセーフ）
    - DuckDB に対する互換性考慮（executemany に空リストを渡さない等）
    - トランザクションでの置換処理（DELETE→INSERT）により冪等性を確保し、部分失敗時に既存スコアを保護
  - レジーム判定 (kabusys.ai.regime_detector)
    - score_regime: ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次算出し market_regime に保存
    - MA 計算は target_date 未満のデータのみを使用（ルックアヘッド防止）
    - マクロセンチメントはマクロキーワードでフィルタしたニュースタイトルを LLM に渡して JSON スコアを取得
    - LLM 呼び出しは失敗時に macro_sentiment = 0.0 として処理継続（フェイルセーフ）
    - 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等パターン（失敗時は ROLLBACK を試行）
    - OpenAI 呼び出しは専用の内部関数を使用し、テスト時に差し替え可能に設計

- データ基盤 (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダーを扱う一連のユーティリティを提供
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar がない場合は曜日ベース（土日を非営業日）でフォールバック
    - next/prev/get_trading_days は市場カレンダーの登録データを優先し、未登録日は曜日フォールバックで一貫した結果を返す
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等に更新。バックフィル（直近 N 日は再フェッチ）や健全性チェックを実装
  - ETL パイプライン (pipeline)
    - ETLResult データクラスを追加（取得・保存件数、品質チェック、エラー情報等を格納）
    - 差分取得、バックフィル、保存、品質チェックのワークフロー設計に準拠
    - jquants_client 経由でのデータ取得・保存を想定
    - 品質チェックは重大度を保持し、致命的問題があっても ETL 自体は継続（呼び出し側で判断）
  - etl モジュールは ETLResult を再エクスポート

- Research（調査）機能 (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す
    - calc_volatility: 20 日 ATR（平均 true range）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から最新財務を取得して PER / ROE を算出（EPS が 0/欠損時は None）
    - 全関数は DuckDB SQL ベースで実装し外部 API にはアクセスしない
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 任意ホライズンの将来リターン（LEAD を利用）を一括取得
    - calc_ic: ファクター値と将来リターンの Spearman（ランク相関）を計算（有効レコード < 3 の場合は None）
    - rank: 同順位は平均ランクを返す実装（丸めで ties 検出を安定化）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能
  - すべての研究関数はルックアヘッドバイアスを避けるため date.today()/datetime.today() を直接参照しない設計

- 内部設計上の配慮
  - DuckDB 互換性への配慮（executemany の空リスト回避、list バインドの回避）
  - トランザクションや例外処理でのフォールバック（ROLLBACK 失敗時の warning ログ）
  - OpenAI API への堅牢なリトライ分類（RateLimit / Connection / Timeout / 5xx）と非再試行エラーの区別
  - JSON Mode の応答を柔軟に復元するためのパースフォールバック（前後の余計なテキストを取り除いて最外の {} を抽出）

### Changed
- （初版のため該当なし）

### Fixed
- レスポンスパースの堅牢化
  - LLM 応答が純粋な JSON でない場合に、外側の最初と最後の波括弧を抽出して復元するフォールバックを追加（news_nlp, regime_detector の両方で扱いを強化）。
- OpenAI SDK の例外ハンドリング改善
  - APIError の status_code を getattr で安全に参照し、5xx 系は再試行対象、それ以外は即時フェイルセーフ（macro_sentiment=0.0 等）とするロジックを導入。

### Security
- （初版リリース、公開する機能に対する明示的なセキュリティ修正はなし）
- 注意点:
  - 環境変数に API キー等の機密情報を格納する想定。必須キー未設定時は ValueError を投げるため、運用手順で .env の管理を厳格化することを推奨。

---

注記:
- 各モジュールはテスト容易性を考慮して設計されています（OpenAI 呼び出しの差し替え可能、DuckDB 接続注入など）。
- 実運用前に J-Quants / OpenAI の API キーや Slack 等の連携設定を .env に正しく設定してください（Settings の必須プロパティ参照）。