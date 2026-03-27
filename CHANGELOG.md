CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-27
--------------------

Added
- 初回リリース。以下の主要機能を追加。
  - パッケージ初期化
    - kabusys パッケージを公開（__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring。
  - 設定 / 環境変数管理 (kabusys.config)
    - .env ファイルおよび環境変数から設定値を自動ロードする仕組みを実装。
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - .env のパースを堅牢化:
      - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理対応、インラインコメント処理（空白直前の # をコメントと判断）等。
    - 自動ロードのオンオフ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env.local を .env より優先して上書き（既存 OS 環境変数は保護）。
    - Settings クラスを提供（J-Quants / kabuAPI / Slack / DB パス / 環境フラグ等のプロパティを定義）。未設定必須変数は ValueError を発生。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）。
  - AI モジュール (kabusys.ai)
    - news_nlp:
      - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとにセンチメントを算出して ai_scores テーブルへ書き込み。
      - タイムウィンドウ計算（JST ベース、UTC に変換）と記事トリミング（最大記事数 / 最大文字数）。
      - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）とリトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）。
      - レスポンスのバリデーションとスコアの ±1.0 クリップ。部分成功時に既存スコアを保護するため DELETE → INSERT の差し替え戦略を採用。
      - 単体テスト容易化のため _call_openai_api をパッチ差替え可能。
      - calc_news_window ヘルパーを公開。
    - regime_detector:
      - score_regime: ETF 1321（日経225連動）200日移動平均乖離とマクロニュースセンチメント（LLM）を重み合成（MA 70% / マクロ 30%）して市場レジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等書き込み。
      - マクロニュースは raw_news からマクロキーワードでフィルタ（最大 20 記事）、LLM 呼び出しは JSON レスポンスを期待。
      - API エラー・パース失敗時はフェイルセーフとして macro_sentiment=0.0 を使用。
      - リトライ戦略とログ出力を実装。テスト用の差替え可能ポイントあり。
  - Research モジュール (kabusys.research)
    - factor_research:
      - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離を計算。データ不足時は None を返却。
      - calc_volatility: 20 日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出。true_range の NULL 伝播制御など堅牢な計算実装。
      - calc_value: raw_financials から最新財務を取得して PER/ROE を算出（EPS 欠損やゼロは None）。
      - いずれも DuckDB 上の prices_daily / raw_financials のみ参照し、実取引 API にはアクセスしない設計。
    - feature_exploration:
      - calc_forward_returns: target_date から指定ホライズン後の終値に基づく将来リターンを計算（horizons の検証あり）。
      - calc_ic: スピアマン順位相関（IC）を実装。十分な有効レコードがない場合は None を返す。
      - rank / factor_summary: ランク化（同順位は平均ランク）・基本統計量サマリーを提供。
      - pandas 等に依存せず標準ライブラリと DuckDB で実装。
  - Data モジュール (kabusys.data)
    - calendar_management:
      - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装:
        - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
      - DB にカレンダーがあればそれを優先、未登録日は曜日ベース（平日）でフォールバックする一貫したロジック。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を更新（バックフィル・健全性チェックを実装）。
      - 最大探索日数やバックフィル日数などの安全パラメータを用意。
    - pipeline / etl:
      - ETLResult dataclass を実装（取得件数・保存件数・品質問題・エラー等を集約）。to_dict メソッドで品質問題をシリアライズ可能。
      - ETL パイプラインの基本ユーティリティ（差分取得・保存・品質チェックの設計方針ドキュメント化）。
      - DuckDB 特性を考慮した実装（executemany に空リストを渡さない等の互換性対策）。
    - jquants_client との連携ポイントを想定（fetch/save 呼び出しを利用するデザイン）。
  - その他
    - DuckDB を前提とした SQL/Python 実装とロギング（logger）を各モジュールに導入。
    - 各所で「ルックアヘッドバイアス防止」の設計方針を明示（datetime.today()/date.today() を参照しない実装方針を採用している箇所あり）。
    - OpenAI クライアント呼び出しは JSON Mode を利用し、厳密な JSON レスポンスを期待するプロンプト設計。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Removed
- 新規リリースのため該当なし。

Security
- OpenAI API キーや外部サービスの資格情報は環境変数経由で取得する設計。必須パラメータ未設定時は ValueError を発生させる（明示的な失敗）。

Notes / 重要な設計決定
- 自動ロードされる .env の優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き禁止）。
- OpenAI 連携は失敗時に例外を投げずフェイルセーフ（0.0 などの中立値）を使ってパイプライン継続する箇所がある（運用上の可用性重視）。
- DuckDB のバージョン依存を考慮した実装（executemany 空リスト回避や date 型取り扱いの互換性処理など）。
- テストのしやすさを意識して、外部 API 呼び出しポイント（_call_openai_api など）を patch 可能にしている。

Contributing
- バグ修正や機能追加は SemVer に従い、各コミット・PR に対応する CHANGELOG エントリを追加してください。