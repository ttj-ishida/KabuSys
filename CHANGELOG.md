# Changelog

All notable changes to this project will be documented in this file.

このCHANGELOGは Keep a Changelog 準拠の形式で記載しています。  
各リリースで行われた主要な追加・変更・修正点を日本語でまとめています。

[Unreleased]
- なし

[0.1.0] - 2026-03-29
---------------------------------
Added
- 初期リリース。パッケージ名 kabusys、バージョン 0.1.0 を定義。
  - パブリックインターフェース: kabusys.__all__ = ["data", "strategy", "execution", "monitoring"]

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定自動読み込みを実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env のパーサーを実装（export KEY=val、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱い等に対応）。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等の取得・バリデーションを行う。
  - 必須変数未設定時は明瞭な ValueError を送出。

- ニュース NLP と市場レジーム判定 (kabusys.ai)
  - news_nlp.score_news:
    - ニュース記事の時間ウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）と、銘柄ごとの記事集約ロジックを実装。
    - OpenAI（gpt-4o-mini）の JSON Mode を用いてバッチ（最大 20 銘柄/チャンク）でセンチメントスコアを取得。
    - スコアのバリデーション・クリップ（±1.0）・部分更新（DELETE → INSERT）を実装し、DuckDB の executemany の制約（空リスト不可）に配慮した実装。
    - API 呼び出しは再試行（429/ネットワーク断/タイムアウト/5xx 共通）を行い、失敗時はスキップして継続（フェイルセーフ）。
    - テスト容易性のため api_key 注入や _call_openai_api のモック差し替えを想定。

  - regime_detector.score_regime:
    - ETF 1321 の MA200 乖離（直近 200 日）と news_nlp によるマクロセンチメントを重み付け合成し、市場レジーム（bull/neutral/bear）を日次で判定。
    - OpenAI API 呼び出しに対して再試行・バックオフを実装。API 失敗時は macro_sentiment=0.0 として継続。
    - 計算結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK を試行）。
    - ルックアヘッドバイアスを避ける設計（datetime.today()/date.today() を直接参照しない、クエリで date < target_date を徹底）。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離の算出（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、ATR/価格、20 日平均売買代金、出来高比などの算出。
    - calc_value: raw_financials から直近財務データを取得して PER / ROE を計算。
    - DuckDB の SQL とウィンドウ関数を活用した高速処理設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）に対する将来リターンを一括で取得。
    - calc_ic: スピアマンランク相関（IC）を実装（有効レコード 3 件未満なら None）。
    - rank: 同順位は平均ランクで処理するランク付けユーティリティ（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する集計ユーティリティ。
  - すべて標準ライブラリ・DuckDB ベースで実装（pandas 等に依存しない）。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - market_calendar を元にした営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新（バックフィル・健全性チェック含む）。
  - pipeline / etl:
    - ETLResult データクラスを実装（ETL の取得数 / 保存数 / 品質問題 / エラー集約）。
    - ETL ユーティリティ（差分更新、バックフィル、品質チェック設計方針）を含むパイプライン土台を実装。
    - jquants_client との連携を想定した保存処理の呼び出し箇所を用意。
  - data.etl モジュールは ETLResult を再エクスポート。

Changed
- 設計方針・堅牢性に関する注記を各モジュールに明示：
  - ルックアヘッドバイアス防止の徹底（関数は target_date を明示的に受け取る）。
  - OpenAI 呼び出しは失敗に対してフォールバック（例: macro_sentiment=0.0）して処理を継続。
  - DuckDB の互換性考慮（executemany に空リストを渡さない等）。
  - トランザクション処理（BEGIN / COMMIT / ROLLBACK）により DB 一貫性を確保。

Fixed
- 初期実装段階での運用上の堅牢性向上（想定される問題に対するフォールバック・ログ出力・再試行の実装）。
  - OpenAI API の 5xx・タイムアウト・レート制限に対する指数バックオフ再試行を実装。
  - レスポンスの JSON パース失敗時に復元処理（最外側の {} を抽出するなど）を追加し、誤差を低減。
  - raw_news 取得時の時間ウィンドウ処理・UTC/タイムゾーンの明確化により時間基準のぶれを修正。

Security
- 環境変数管理において OS 環境変数を保護するための protected セットを導入（自動 .env 上書き時に保護）。
- API キーは明示的に引数注入可能（テスト用）かつ環境変数参照で解決。未設定時は ValueError を投げ明示。

Notes / Implementation details
- OpenAI は gpt-4o-mini を想定しており、JSON Mode（response_format={"type":"json_object"}）で整形された応答を期待する設計。
- 多くの処理で「失敗したら止めない」方針（部分的な API 失敗はログを出してスキップ）を採用し、バッチ全体の継続性を優先。
- 単体テストを容易にするため、外部 API 呼び出しポイント（_call_openai_api 等）をモック差し替え可能に実装。

---------------------------------

注: 本 CHANGELOG は現在のコードベース（初期実装）から推測して作成しています。将来的に機能追加や修正が行われる際は、リリースごとにこのファイルを更新してください。