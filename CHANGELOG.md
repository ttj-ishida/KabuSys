# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを使用します。

なお、以下はコードベースから推測して作成した初期リリースの変更点記録です。

# 未リリース
（なし）

# [0.1.0] - 2026-04-01
初期リリース。

## 追加
- パッケージの基本構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーは export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理などに対応。
  - Settings クラスを提供（J-Quants、kabuステーション、Slack、DBパス、監視閾値、環境設定、ログレベルなどのプロパティ）。
  - 必須環境変数が未設定の場合は明確な ValueError を発生。

- データプラットフォーム機能 (kabusys.data)
  - ETL パイプライン用の ETLResult 型を公開（kabusys.data.pipeline の再エクスポート）。
  - pipeline モジュール（差分取得、保存、品質チェックの基礎構造、ETLResult データクラス）を実装。
  - calendar_management モジュールを実装
    - JPX カレンダーの夜間差分更新ジョブ (calendar_update_job)。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の営業日判定・探索ユーティリティ。
    - market_calendar テーブルが未取得の場合は曜日ベースのフォールバックを採用。
    - DB 登録あり→DB優先、未登録日→曜日ベースフォールバックの一貫した振る舞い。
    - 最大探索日数やバックフィル、健全性チェック等の安全策を導入。

- 研究 (research) モジュール (kabusys.research)
  - factor_research:
    - モメンタム（1M, 3M, 6M）、200日MA乖離、ATR（20日）、平均売買代金、出来高比率などの算出関数（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を使った SQL ベースの実装。データ不足時は None を返す設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）。
    - IC（Information Coefficient）計算（calc_ic） — スピアマンのランク相関。
    - factor_summary（統計要約）、rank（同順位は平均ランク）等のユーティリティ。
  - kabusys.research パッケージから zscore_normalize 等を再エクスポート。

- AI（自然言語処理）機能 (kabusys.ai)
  - news_nlp:
    - raw_news と news_symbols を使い、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）に送信してセンチメント（ai_score）を取得。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄当たりの記事数・文字数上限によるトリム処理、チャンク単位での頑健なリトライ（429 / ネットワーク / タイムアウト / 5xx の指数バックオフ）。
    - レスポンスのバリデーション（JSON 抽出、results キー、スキーマ検証、未知コードの無視、数値検査）、スコアを ±1 にクリップ。
    - DB への書き込みは部分失敗時に既存スコアを保護するため、取得済みコードのみ DELETE → INSERT（冪等性を考慮）。
    - テスト容易性のため _call_openai_api を差し替え可能に実装。
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily, raw_news を参照して ma200_ratio を計算、マクロ記事はキーワードでフィルタして上限件数まで取得。
    - OpenAI（gpt-4o-mini）を用いた JSON 出力によるマクロセンチメント評価。API 障害時はマクロスコアを 0.0 にフォールバックするフェイルセーフ。
    - レジーム結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。API キーは引数または OPENAI_API_KEY 環境変数で指定。

- 汎用・設計上の配慮
  - DuckDB を主要な分析用内蔵データベースとして想定（多くの関数は DuckDB 接続を引数に受け取る）。
  - ルックアヘッドバイアス回避: datetime.today() / date.today() を内部参照しない設計（すべて target_date を明示的に受け取る）。
  - 多くの API 呼び出しについて「失敗時に例外を上位に投げずにフェイルセーフ挙動をする」実装（ログ記録後のデフォールト値採用）。
  - テストのしやすさを考慮し、外部 API 呼び出し箇所をモック差し替えできる形で実装。

## 変更
- 初期リリースのため過去リリースからの変更はなし。

## 修正
- 初期リリースのため過去リリースからの修正はなし。

## 既知の制限 / 注意点
- OpenAI クライアントは gpt-4o-mini を既定モデルに利用する設計になっているが、API 利用に必要なキー（引数 or OPENAI_API_KEY）が必須。
- DuckDB の executemany に関するバージョン差異を考慮したワークアラウンドを使用（空リスト渡しの挙動に注意）。
- news_nlp/regime_detector の LLM 呼び出しは API レート制限・レスポンス不整合を考慮した防御的実装になっているが、品質向上のためプロンプトやパースロジックの調整が将来的に必要となる可能性がある。
- calendar_management は market_calendar が未取得の場合に曜日フォールバックを行うため、正確な祝日情報がない環境では結果が簡易判定になる。

## セキュリティ
- 環境変数（APIキー等）を必要とする機能があるため、運用時は .env 等の管理に十分注意してください（Settings は必須未設定時に ValueError を投げます）。

（以上）