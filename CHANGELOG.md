保持版式: Keep a Changelog 準拠

以下は提示されたコードベースから推測して作成した CHANGELOG.md（日本語）です。

CHANGELOG
=========

すべての変更は慣例に従い semver に基づいて記載しています。  
主に初回公開相当の機能実装をまとめています。

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" 登録。公開モジュール: data, strategy, execution, monitoring。

- 環境設定・自動 .env ロード機能（kabusys.config）
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml）から自動読込。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パースで以下に対応:
    - 空行・コメント行（#）の無視、export KEY=val 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなしの場合のインラインコメント扱い（'#' の前が空白／タブ時にコメントと認識）。
  - Settings クラスを提供（プロパティで各種設定を取得）:
    - J-Quants, kabu ステーション API、Slack、データベースパス、監視閾値、環境 / ログレベル判定等。
    - 必須項目は _require() で明示的に ValueError を発生させる。
    - KABUSYS_ENV, LOG_LEVEL のバリデーション実装。
    - Path 型プロパティは expanduser() を適用。

- AI: ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - raw_news / news_symbols テーブルを集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを取得。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）実装（calc_news_window）。
  - バッチ処理（最大 20 銘柄/リクエスト）、1銘柄あたりの最大記事数・最大文字数制限を実装(_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
  - API 呼び出しでの堅牢化:
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。
    - レスポンスは厳密な JSON を期待しつつ、前後余分テキストが混入するケースに対する冗長復元ロジックを実装。
    - スコアは ±1.0 にクリップ。
    - バリデーションに失敗した場合はエラーにせずスキップ（フェイルセーフ）。
  - DuckDB への書き込みは冪等に実行（対象コードのみ DELETE → INSERT）し、部分失敗時に既存スコアを保護。
  - テスト容易化のため _call_openai_api を内部で用意し patch/mocking しやすく設計。

- AI: 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
  - MA 計算は target_date 未満のみ参照しルックアヘッドを防止（データ不足時は ma200_ratio = 1.0 として中立扱い）。
  - マクロニュース抽出はキーワードによるフィルタ（_MACRO_KEYWORDS）と上限記事数。
  - OpenAI 呼び出し（gpt-4o-mini JSON mode）に対して同様にリトライ・フェイルセーフを実装。API 失敗時は macro_sentiment=0.0 で継続。
  - 最終的なレジーム評価はクリップしてラベル付けし、market_regime テーブルに冪等書き込み（BEGIN / DELETE / INSERT / COMMIT with ROLLBACK handling）。

- Research: ファクター計算群（kabusys.research）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を算出。
    - calc_value: raw_financials と株価を組み合わせて PER, ROE を算出（EPS が 0 / null の場合は PER を None）。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD により一括取得。
    - calc_ic: スピアマンランク相関（IC）をコードで結合して計算、データ不足時は None を返す。
    - rank: 同順位は平均ランクとする実装（小数丸めで ties の誤判定を防止）。
    - factor_summary: count/mean/std/min/max/median を算出するユーティリティ。
  - いずれも DuckDB 接続のみ参照し外部発注や実口座へのアクセスは行わない設計。

- Data: カレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーを管理する market_calendar テーブル向けユーティリティ群を実装:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day など営業日判定 API。
  - DB にカレンダーがない場合は土日ベースでフォールバック。
  - next/prev/search は最大探索日数の上限（_MAX_SEARCH_DAYS）を持ち無限ループを防止。
  - calendar_update_job: J-Quants クライアント経由で差分取得して market_calendar を冪等保存、バックフィルの考慮、健全性チェック実装。

- Data: ETL パイプライン基盤（kabusys.data.pipeline / etl）
  - ETLResult データクラスを定義（ETL の取得数・保存数・品質問題・エラーの集約）。
  - 差分更新、バックフィル、品質チェックの設計方針を実装に反映（jquants_client, quality モジュールと連携する想定）。
  - DuckDB テーブル存在チェック、最大日付取得ユーティリティなど補助関数。

- その他
  - duckdb への SQL 実行における互換性考慮（executemany に空リストを渡さない等）を反映。
  - ロガー出力を各モジュールで適切に追加（info/warning/debug）。
  - 多くの処理で「ルックアヘッドバイアス防止」の設計方針を明記・実装（datetime.today()/date.today() を直接参照しない等）。
  - OpenAI とのやり取りを JSON Mode で行う方針とし、レスポンスの堅牢なパースとバリデーションを実装。
  - テスト容易性のため、内部 API 呼び出しポイント（_call_openai_api 等）を差し替え可能に設計。

Changed
- （初版につき該当なし）

Fixed
- （初版につき該当なし）

Security
- （該当なし）

Notes / 実装上の注意
- 多くの外部 API 呼び出し（OpenAI, J-Quants）部分はクライアント呼び出しを想定しており、実行には該当 API キーやクライアント実装が必要です。
- DuckDB のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）が前提となっています。実行環境でのテーブル定義が必要です。
- OpenAI API のエラーや SDK のバージョン差分（status_code の取り扱い等）に配慮した実装がなされていますが、実環境での動作確認と適切なログ監視を推奨します。

（今後のリリース候補）
- strategy / execution / monitoring 周りの具体的な実装（提示コードの __all__ に含まれるが本差分には未提供）を追加する予定。
- ai/regime_detector と news_nlp の LLM プロンプトやモデル設定のチューニング、テストカバレッジ拡充を検討。