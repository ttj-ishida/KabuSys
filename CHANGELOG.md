Keep a Changelog
===============

すべての注目に値する変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  
このプロジェクトはセマンティックバージョニングを使用しています。

## [0.1.0] - 2026-03-28

初回公開リリース。本バージョンで導入された主な機能、設計方針、堅牢化変更点を以下にまとめます。

### Added
- パッケージ基盤
  - kabusys パッケージ初期公開。__version__ = 0.1.0。
  - パッケージの公開 API として data, research, ai, execution, strategy, monitoring 等を想定した __all__ を設定。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数を使った設定読み込みを実装。
  - 自動ロードの制御: KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - プロジェクトルートの検出: .git または pyproject.toml を起点に探索することで CWD に依存しないロードを実現。
  - .env 読み込み順序: OS環境変数 > .env.local > .env（.env.local は上書き許可）。
  - .env の高度なパース機能:
    - export KEY=val 形式対応
    - シングル/ダブルクォートの中のエスケープ処理対応
    - 行末のコメント処理（クォート有無に応じた挙動）
  - 保護されたキーセットを用いた上書き制御（OS 環境変数の保護）。

- 設定アクセスラッパー（Settings クラス）
  - J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供。
  - 必須設定未定義時は明示的に ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値のバリデーション）。
  - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI 関連
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを算出して ai_scores テーブルへ書き込み。
    - JST ベースのニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を実装。
    - バッチ処理: 1 API コールあたり最大 20 銘柄、1銘柄あたり記事最大 10 本・最大 3000 文字にトリムして送信。
    - JSON モードを用いた厳密なレスポンス期待（レスポンス検証ロジックと復元処理を実装）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフでのリトライ。
    - レスポンス検証: results 配列・code と score の存在チェック・未知コードの無視・スコアの ±1.0 でクリップ。
    - テスト容易性のため _call_openai_api を差し替え可能に実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードフィルタ（日本・米国系の主要語句）で raw_news を抽出し、OpenAI（gpt-4o-mini）で macro_sentiment を算出。
    - レジームスコアの合成、閾値判定（bull/bear に使うしきい値を定義）。
    - DB への冪等的書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理を実装。
    - API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - テストで置換可能な _call_openai_api とリトライロジック、ログ出力を実装。

- Research（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算関数を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率の計算（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率の計算（欠損時の扱いに注意）。
    - calc_value: raw_financials を用いた PER, ROE の計算（EPS=0 等は None）。
  - feature_exploration: 将来リターン計算、IC（Spearman の ρ）計算、統計サマリー、ランク変換ユーティリティを実装。
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度の SQL で取得。
    - calc_ic: factor と forward を code で結合してスピアマンρ を算出（有効データ 3 件未満は None）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
    - rank: 平均ランク（同順位は平均ランク）での変換を実装。

- Data（kabusys.data）
  - calendar_management: JPX カレンダー管理、営業日判定関数を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar データがない場合の曜日ベースフォールバックを実装。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存する夜間バッチロジック（バックフィル・健全性チェックあり）。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラーの集約）。
    - pipeline: 差分取得・保存・品質チェックに関するユーティリティ（データ最終日取得等）。

### Changed
- （該当なし：初回リリースのため過去変更はなし）

### Fixed / Hardening
- .env パーサーの堅牢化（config._parse_env_line）
  - クォート内のバックスラッシュエスケープ処理を実装して誤解析を防止。
  - コメント判定ロジックを改善（クォート有無で振る舞いを分離）。
  - export プレフィックス対応でシェル形式の .env 互換性を向上。

- DB 書き込みの安全化
  - market_regime / ai_scores 等への更新でトランザクション（BEGIN/COMMIT/ROLLBACK）および部分削除→挿入のパターンを導入し、冪等性と部分失敗時のデータ保護を実現。
  - DuckDB の executemany に対する互換性（空リストの回避）を考慮した実装。

- OpenAI 呼び出しの堅牢化
  - JSON mode を想定したパース回復処理（前後に余分なテキストが混ざるケースの復元）。
  - APIError の status_code の扱いを安全化（getattr を使用して互換性を保つ）。
  - 5xx・ネットワーク・429・タイムアウトを対象に指数バックオフリトライを実装。非 5xx エラーは即時フォールバック。

- ルックアヘッドバイアスに関する設計方針徹底
  - 日付計算処理が datetime.today() / date.today() を直接参照しない設計（target_date ベースでの明示指定）をモジュール全体で維持。

### Performance / Implementation notes
- DuckDB を主要なデータ保存/クエリ機構として採用。大量データのウィンドウ集計は SQL で実行してパフォーマンスを狙う設計。
- ニュース NLP は銘柄ごとの記事を結合・トリムして送ることでトークン肥大化を抑制。
- バッチサイズやウィンドウ長、リトライ上限等は定数化されており、運用に合わせて調整可能。

### Security
- OpenAI API キー未設定時は ValueError を送出して明示的に失敗させる設計（安全性確保）。
- 環境変数の自動読み込みは無効化可能（CI/テスト環境向け）。
- 環境変数の上書き制御により OS 環境変数が保護される仕組みを導入。

---

注記:
- 本 CHANGELOG はソースコードの内容・ドキュメンテーション文字列から推測して作成したものであり、実際のリリースノートや運用ポリシーに応じて編集・補足してください。