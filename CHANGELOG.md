CHANGELOG
=========

すべての注目すべき変更点はここに記録します。  
このファイルは "Keep a Changelog" のフォーマットに準拠しています。

フォーマット:
- 追加 (Added) — 新機能
- 変更 (Changed) — 既存機能の変更
- 修正 (Fixed) — バグ修正
- 非推奨 (Deprecated) — 廃止予定の機能
- 削除 (Removed) — 削除された機能
- セキュリティ (Security) — セキュリティ関連

[Unreleased]
------------

- （現時点で未リリースの修正・改善点をここに記載します）

[0.1.0] - 2026-04-01
-------------------

Added
- 初期リリース: KabuSys 日本株自動売買用ライブラリを公開。
- パッケージ情報:
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - 主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring
- 環境設定管理 (src/kabusys/config.py):
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を基準）を検出して .env/.env.local を読み込み（優先度: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - .env パーサーは export KEY=val 形式、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱いなどに対応。
  - 各種設定プロパティを提供（J-Quants、kabuステーション、Slack、DBパス、監視しきい値、環境・ログレベル判定など）。
  - 環境値検証（KABUSYS_ENV の許容値, LOG_LEVEL の許容値）を実施。
- AI モジュール (src/kabusys/ai):
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメント評価。
    - ニュースウィンドウ計算（JST ベース → DB 上は UTC naive datetime に変換）を calc_news_window で提供。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）と各銘柄のトリム（最大記事数 / 最大文字数）を実装。
    - 再試行（429、ネットワーク障害、タイムアウト、5xx）を指数バックオフで実施。
    - レスポンスの堅牢なバリデーションとスコアの ±1.0 クリップ。
    - API キー注入可能（api_key 引数または OPENAI_API_KEY 環境変数）。
    - フェイルセーフ: API/パース失敗時は該当チャンクをスキップして処理継続。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）判定。
    - マクロセンチメントは OpenAI（gpt-4o-mini、JSON Mode）で記事タイトル群を評価。記事がない場合は LLM 呼び出しをスキップして 0.0 を採用。
    - API 呼び出し用に堅牢なリトライ/バックオフとエラーハンドリングを実装（フェイルセーフで macro_sentiment=0.0 にフォールバック）。
    - DuckDB を用いた冪等的な書き込み（BEGIN / DELETE / INSERT / COMMIT）で market_regime テーブルを更新。
- 研究（Research）モジュール (src/kabusys/research):
  - factor_research.py
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離の計算（prices_daily を参照）。
    - ボラティリティ/流動性: 20 日 ATR、ATR/%、20 日平均売買代金、出来高比率の計算。
    - バリュー: PER（EPS 不在/0 は None）、ROE を raw_financials と prices_daily から計算。
    - DuckDB SQL ウィンドウ関数を活用した効率的な実装。
  - feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン）とそれを用いた IC 計算（スピアマンの順位相関）、ランク変換ユーティリティ、ファクター統計サマリーを提供。
    - pandas 等の外部依存なしで標準ライブラリのみで実装。
  - research パッケージは主要ユーティリティを再エクスポート（calc_momentum 等）。
- データ（Data）モジュール (src/kabusys/data):
  - calendar_management.py
    - JPX マーケットカレンダーの管理ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が未取得時は曜日ベースのフォールバック（土日を非営業日扱い）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィル/健全性チェック実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを定義し、ETL の取得数・保存数・品質問題・エラーを集約。
    - 差分取得、backfill、品質チェック（quality モジュール連携）を行う設計（実装の大枠を提供）。
    - etl.py で ETLResult を再エクスポート。

Changed
- なし（初期リリース）

Fixed
- なし（新規追加のため過去の修正は無し）

Known issues / Notes
- DuckDB 互換性に関する注意:
  - executemany に空リストを渡せない古い DuckDB バージョンを考慮して保護ロジックを実装（空チェックを行う）。
- フェイルセーフ設計:
  - LLM/API 呼び出し失敗時は例外をスローせずロギングしてスコア 0.0 を使用するなど、外部 API に依存する処理は部分失敗時にシステム全体が停止しないように設計されています。
- テスト容易性:
  - OpenAI API 呼び出し部分は個別関数（_call_openai_api）に抽象化しており、unittest.mock.patch により差し替え可能。
- 未完／潜在的なバグ（注意喚起）:
  - src/kabusys/data/pipeline.py の末尾に不完全な行（return date.fro）が存在しており、これはタイプミス/未完のコードと認識されます。実行時にエラーを引き起こす可能性があるため、修正が必要です。
  - その他、production 環境での検証や長期運用でのエッジケース確認（極端なカレンダー差分、LLM レート制限による部分失敗など）を推奨します。

Security
- 本リリースにおける既知のセキュリティ脆弱性は報告されていません。ただし、API キーや機密情報の管理は .env / 環境変数を通じて行うため、運用時は適切なシークレット管理を行ってください。

Authors
- コードベースから推測される主な機能実装者（詳細はリポジトリのコミット履歴を参照してください）。

ライセンス
- リポジトリ内の LICENSE を参照してください。

コメント・貢献
- バグ報告・機能提案は issue を通じてお願いします。特に pipeline の未完部分と DuckDB のバージョン依存に関するテストケースを歓迎します。