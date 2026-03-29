CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。重要な設計方針や注意点も併記しています。

未リリース
---------

（なし）

0.1.0 - 2026-03-29
-----------------

Added
- 初回リリース: KabuSys — 日本株自動売買・データ基盤向けライブラリ（バージョン 0.1.0）。
  - パッケージ公開情報:
    - パッケージ名: kabusys
    - __version__: 0.1.0
    - パブリックサブパッケージ: data, research, ai, execution, monitoring, strategy（うち一部は実装済み）

- 環境設定 / 起動周り (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索するため、CWD に依存しない動作。
  - .env パーサーの強化:
    - "export KEY=val" 形式対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理対応
    - クォートなしでのインラインコメント解析（# の前が空白／タブの場合にコメント扱い）
    - 無効行のスキップ
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト等で使用）
  - OS 環境変数を保護するための protected 値扱い（上書き防止）
  - Settings クラスを提供し、必須値は _require() で ValueError を送出:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など
  - env / log_level 等は許可値チェックを実施
  - データベースパスのデフォルト（DuckDB / SQLite）を提供

- データプラットフォーム関連 (kabusys.data)
  - カレンダー管理 (calendar_management):
    - market_calendar を利用した営業日判定 API を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダー登録がない場合は曜日（土日）ベースでフォールバック
    - calendar_update_job により J-Quants から差分取得して冪等保存（バックフィル / 健全性チェック含む）
    - 最大探索日数やバックフィル等の安全装置を実装（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）
  - ETL / パイプライン (pipeline, etl):
    - ETLResult データクラスを公開（etl モジュールから再エクスポート）
    - 差分取得・バックフィル・保存（jquants_client 経由で idempotent 保存）・品質チェックの設計を反映
    - DuckDB に対する互換性配慮（executemany に空リストを渡さない等）
    - _get_max_date 等のユーティリティを実装

- AI / ニュース NLP・レジーム判定 (kabusys.ai)
  - news_nlp:
    - ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini, JSON mode）でセンチメント評価を行い ai_scores テーブルへ保存
    - 時間ウィンドウ設計（JST ベースの前日 15:00 ～ 当日 08:30 を UTC に変換して比較）
    - バッチ送信（1回最大 20 銘柄）、1銘柄あたり記事数 / 文字数制限でトークン膨張へ対策
    - JSON レスポンスのバリデーションと安全なパース（余分な前後テキストが混入する場合の復元処理含む）
    - 非数値や無限値を除外、スコアは ±1.0 にクリップ
    - API の一時エラー（429 / ネットワーク / タイムアウト / 5xx）に対する指数バックオフとリトライ
    - 取得したスコアはトランザクションで既存行を置換（DELETE → INSERT）して部分失敗時の保護を実現
    - テスト容易性のため _call_openai_api をモック可能
  - regime_detector:
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム判定（bull/neutral/bear）を行う score_regime を実装
    - ma200_ratio 計算は target_date 未満のデータのみを使用しルックアヘッドを防止
    - マクロニュース抽出（キーワードリスト）→ LLM 呼び出しで macro_sentiment を評価
    - API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフ
    - 書き込みは market_regime テーブルへ冪等処理（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK を試行して例外を伝播

- 研究用モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離の計算（データ不足時は None）
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出
    - calc_value: raw_financials と当日の株価から PER / ROE を算出（EPS が無効な場合は None）
    - DuckDB SQL を中心に純粋なオフライン分析関数を実装（注文系 API へアクセスしない）
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（有効データが 3 件未満なら None）
    - rank: 平均ランクで同順位を扱う実装（浮動小数丸めで ties の誤検出を防止）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー

- 実装上の設計方針（全体）
  - ルックアヘッドバイアス防止: datetime.today() / date.today() を計算内部で直接参照しない設計（target_date を明示）
  - DuckDB を第一選択のローカル分析 DB として想定。SQL と Python の組合せで集約・ウィンドウ処理を実行
  - OpenAI（gpt-4o-mini）を JSON mode で利用し、レスポンスの厳密検証を行う
  - API 呼び出しは堅牢に（リトライ・バックオフ・フェイルセーフ・ログ出力）
  - テストしやすさを配慮（API 呼び出し関数の差し替えポイントを用意）

Notes / 補足
- monitoring / execution / strategy などのサブパッケージは __all__ に含まれるが、今回のコードスニペットでは一部機能のみが実装／公開されている想定です（将来的な機能追加・実装拡張予定）。
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError を送出するため、運用時は環境設定が必須です。
- DuckDB のバージョン差異（executemany の空リスト扱い等）に対する互換性考慮が各所に実装されています。

今後の予定（暗黙のロードマップ）
- monitoring / execution 周りの実装拡充（実際の発注フロー・モニタリング）
- デプロイ向けの運用ドキュメント整備（Docker / CI / バックアップ等）
- J-Quants / kabu ステーション連携の拡張と自動化
- AI モデル／プロンプトのチューニング、評価パイプラインの追加

--- 

（この CHANGELOG はコードの実装内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。）