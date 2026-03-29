Keep a Changelogに従い、コードベースから推測した変更履歴（日本語）を作成しました。初回リリースとしてバージョン 0.1.0 を記載しています。必要に応じて日付や追加項目を編集してください。

CHANGELOG.md
=============
すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。
（https://keepachangelog.com/ja/1.0.0/）

当リポジトリに含まれる主な機能群：
- 環境設定読み込み・検証（kabusys.config）
- データ管理 / ETL / カレンダー（kabusys.data.*）
- AI ベースのニュースセンチメント & 市場レジーム判定（kabusys.ai.*）
- 研究用ファクター計算・特徴量探索（kabusys.research.*）
- DuckDB を用いた SQL ベースの分析

Unreleased
----------
- なし

0.1.0 - 2026-03-29
------------------
Added
- パッケージ初回公開（kabusys v0.1.0）
  - パッケージ初期化: __version__ を "0.1.0" に設定し、主要サブパッケージを公開。
- 環境設定 / ローダー（kabusys.config）
  - .env / .env.local ファイル自動読込機能を実装（読み込み優先度: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .git または pyproject.toml を起点にプロジェクトルートを探索する実装（CWD 非依存）。
  - .env パーサー実装:
    - コメント行・空行のスキップ、export KEY=val 形式対応。
    - シングル/ダブルクォートとバックスラッシュエスケープ処理のサポート。
    - クォートなし行でのインラインコメント判定（直前が空白またはタブの場合）。
  - 環境変数必須チェック関数 _require を提供（未設定時は ValueError）。
  - Settings クラスを公開（プロパティで各種設定を取得）:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティ。
    - KABUSYS_ENV 値検証（development/paper_trading/live のみ許容）。
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev ヘルパー。
- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp.score_news）を実装:
    - 指定の時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当）で raw_news を集約し、
      銘柄ごとに記事を結合して OpenAI (gpt-4o-mini) に送信、センチメントを ai_scores に書き込み。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたり記事数・文字数制限（トリム）を実装。
    - JSON Mode のレスポンスを堅牢にパース（前後余計文字の抽出や型検証を含む）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - DuckDB の executemany の制約を考慮した安全な DELETE→INSERT ロジック（部分失敗で既存スコア保護）。
    - API キー注入（api_key 引数または環境変数 OPENAI_API_KEY）。
    - フェイルセーフ: API 失敗時は該当チャンクをスキップして処理継続。
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）を実装:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して
      日次でレジーム（bull/neutral/bear）を判定し market_regime に冪等的に保存。
    - マクロニュース抽出（キーワードベース）と OpenAI 呼び出し（gpt-4o-mini, JSON Mode）。
    - API エラー時の安全フォールバック（macro_sentiment = 0.0）。
    - リトライ／指数バックオフ、5xx とそれ以外のハンドリング差別化、JSON パースとバリデーションに対応。
    - ルックアヘッドバイアス回避（target_date 未満のデータのみ使用、datetime.today()/date.today() 非参照）。
- 研究（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）を実装:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（200 日）を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出（EPS 0/欠損時は None）。
    - DuckDB SQL ウィンドウ関数を活用した効率的実装、ルックアヘッドバイアス回避。
  - 特徴量探索（kabusys.research.feature_exploration）を実装:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（存在しない場合は None）。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算。必要レコード数の検証。
    - rank: 同順位は平均ランク処理。小数丸めで ties の安定化。
    - factor_summary: カラム別 count/mean/std/min/max/median を計算。
    - 標準ライブラリのみで依存性を抑えた実装。
- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）を実装:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベースでフォールバック（週末を休場扱い）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に保存（バックフィル・健全性チェックあり）。
    - 最大探索日数・バックフィル期間・先読み設定などの安全制約を実装。
  - ETL / パイプライン（kabusys.data.pipeline / etl）:
    - ETLResult データクラスを公開（取得数、保存数、品質問題、エラー一覧を保持）。
    - 差分更新ロジック、バックフィル、品質チェック（quality モジュール連携）に対応。
    - 最終取得日の取得ユーティリティ、テーブル存在チェック等を提供。
  - jquants_client 連携用のラッパーを前提とした保存処理（IDempotent 保存）を念頭に設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし。ただし多くの箇所でフォールバック・例外処理・トランザクション保護を実装）

Security
- 環境変数取り扱い:
  - OS 側の既存環境変数を保護する設計（.env を上書きしない / .env.local で上書き可能、保護セットを利用）。
  - OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を要求（未設定時は ValueError）。

Notes / 実装上の注意
- DuckDB のバージョン依存性を考慮（executemany に空リストを渡せない等の対策）。
- OpenAI 呼び出しは Chat Completions（JSON mode）を想定。テスト時は内部 _call_openai_api をモック可能。
- 日付処理はすべて timezone-naive な date/datetime オブジェクトで統一（JST/UTC の変換を明示的に扱う）。
- ルックアヘッドバイアス防止を設計上の基本方針としているため、すべての分析系関数は target_date に対して過去データのみ参照する。

貢献
- 初回リリース（内部実装に基づくドキュメント化）。今後の追加機能・修正はこの CHANGELOG に追記してください。