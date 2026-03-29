CHANGELOG
=========

すべての変更点は "Keep a Changelog" の形式に準拠して記載しています。  
フォーマット: [Unreleased] / [0.1.0] - YYYY-MM-DD ... の順。

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-29
-------------------

初期リリース。パッケージ名: kabusys (バージョン 0.1.0)

Added
- 基本パッケージ構成を追加
  - src/kabusys/__init__.py にパッケージメタ情報（__version__ = "0.1.0"）と公開サブパッケージ一覧を追加。
- 環境設定管理モジュールを追加（kabusys.config）
  - .env ファイル（.env, .env.local）および環境変数からの設定自動ロード機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml）に基づく自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パースは export 構文・クォート・コメント処理・エスケープ対応。
  - Settings クラスを公開し、J-Quants / kabuステーション / Slack / DB パス / 環境モード（development/paper_trading/live）等のプロパティを提供。
  - 必須環境変数未設定時は ValueError を投げる保護機能を実装。
- AI モジュールを追加（kabusys.ai）
  - news_nlp (score_news)
    - raw_news / news_symbols を集約して銘柄別ニュースを OpenAI（gpt-4o-mini）の JSON Mode でバッチ解析し、ai_scores に書き込む。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供。
    - バッチサイズ、記事数・文字数制限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスの厳格バリデーションを実装。
    - DuckDB への冪等な書込み（DELETE → INSERT）で部分失敗時に既存データ保護。
  - regime_detector (score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime に書き込む。
    - マクロニュースはキーワードでフィルタし、OpenAI 呼び出しはリトライとフェイルセーフ（失敗時 macro_sentiment=0.0）を採用。
    - ルックアヘッドバイアス回避のため、target_date 未満のデータのみ参照。
  - OpenAI 呼び出しはテスト時に差し替え可能なラッパー関数経由で実施（モジュール間結合を避ける設計）。
- データプラットフォーム関連モジュールを追加（kabusys.data）
  - calendar_management
    - market_calendar に基づく営業日判定（is_trading_day）、翌営業日/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ判定（is_sq_day）を提供。
    - DB 登録値優先、未登録日は曜日（週末）ベースでフォールバックする一貫した挙動。
    - JPX カレンダー差分取得 → market_calendar 更新を行う夜間バッチ（calendar_update_job）を実装。バックフィル／健全性チェックあり。
  - pipeline / etl
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー集約など）。
    - 差分更新・バックフィル・品質チェック（quality モジュール連携）を想定した設計。
  - jquants_client など外部 API クライアントを利用する想定での ID トークン注入や例外取り扱い方針を盛り込んだ設計。
- リサーチモジュールを追加（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比を計算。
    - calc_value: raw_financials から取得した EPS/ROE と株価を組み合わせて PER / ROE を計算。
    - DuckDB SQL ベースで営業日・データ不足時の None ハンドリング等に配慮。
  - feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括取得する効率的クエリ実装。
    - calc_ic: スピアマンのランク相関（IC）計算（None/データ不足 の扱いを厳格に）。
    - rank: 同順位は平均ランクで返す実装（丸め処理で ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する集計ユーティリティ。
- DuckDB を主要なローカル DB として全面的に利用する設計（SQL + Python の組合せで高性能解析）。
- 多くの処理で「ルックアヘッドバイアスを避ける」「API 失敗時のフェイルセーフ」「冪等な DB 書込」「部分失敗時に既存データを保護」などの安全設計を採用。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- 新規リリースのため該当なし。

Notes / 設計上の重要事項
- OpenAI API キーは関数引数から注入可能（テスト容易性）で、引数未指定時は環境変数 OPENAI_API_KEY を参照する実装になっています。未設定時は ValueError を送出します。
- .env 自動ロードはプロジェクトルート検出に依存し、パッケージ配布後も CWD に依存しないよう配慮しています。OS 環境変数は保護（上書き禁止）されます。
- DuckDB の executemany に対する互換性（空リスト不可など）を考慮した実装が含まれています。
- 日付/時間の扱いは全て日付オブジェクト（date）や UTC naive datetime を明示しており、timezone の混入を避けています。
- ログ出力・警告は詳細に実装されており、外部 API エラー時にはログを出して安全にフェイルするようになっています。

今後の予定（想定）
- AI モジュールの出力スキーマ拡張（confidence 等）
- 追加ファクター（PBR、配当利回り）やバックテスト・実行モジュール（strategy / execution / monitoring）の実装拡充
- テストカバレッジの強化と CI 連携

---------
（注）上記は提供されたコードベースを基に推測して作成した CHANGELOG です。実際の開発履歴・リリース日付が異なる場合は適宜調整してください。