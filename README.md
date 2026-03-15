# KabuSys

KabuSys は日本株の自動売買システムの骨組み（スケルトン）です。  
データ取得、取引戦略、注文実行、監視の各コンポーネントに分割されたモジュール構成を提供し、独自のロジックを実装して自動売買システムを構築できるように設計されています。

バージョン: 0.1.0

---

## 主な特徴

- モジュール化された設計
  - data: 市場データの取得・加工を行う層
  - strategy: 売買戦略を実装する層
  - execution: 注文発注・約定管理を行う層
  - monitoring: 稼働状況やパフォーマンスの監視を行う層
- 最小限の骨組みを提供し、拡張して独自の戦略や実行ロジックを組み込める
- パッケージ化された Python モジュールとして利用可能

---

## セットアップ手順

1. 必要条件
   - Python 3.8 以上を推奨
   - （任意）実際の取引 API（例えば証券会社のAPI）や各種ライブラリは別途導入してください

2. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

3. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   # Linux / macOS
   source .venv/bin/activate
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   ```

4. パッケージをインストール（開発モード）
   ```bash
   pip install -e .
   ```
   ※ 依存パッケージがある場合は `requirements.txt` を用意して `pip install -r requirements.txt` を実行してください。

---

## 使い方（基本）

このパッケージは現状「骨組み」なので、各モジュールに具体的な実装を追加して利用します。まずは簡単な利用例を示します。

- パッケージのインポートとバージョン確認
```python
import kabusys
print(kabusys.__version__)  # "0.1.0"
```

- モジュールをインポートして実装を追加する例
```python
# src/kabusys/strategy/my_strategy.py
# ここに戦略クラスや関数を実装する

# 実行時（ユーザー側コード）
from kabusys import data, strategy, execution, monitoring

# 例: data モジュールの関数を呼び、strategy を使ってシグナル生成、
# execution に渡して注文を出す、monitoring で状態を記録する
# （実装は各モジュール内に追加してください）
```

実際の運用では以下を実装してください：
- data: API クライアントやデータ取得関数（例: 株価取得、板情報、約定履歴など）
- strategy: エントリー／イグジットのロジック、リスク管理、ポジション管理
- execution: 注文作成、送信、注文監視（約定、キャンセル等）、取引ログ出力
- monitoring: ログ、メトリクス、アラート（例: Slack/メール通知）

---

## ディレクトリ構成

リポジトリの現状のファイル構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py              # パッケージ定義、バージョン情報
    - data/
      - __init__.py            # データ取得関連の実装をここに追加
    - strategy/
      - __init__.py            # 戦略実装をここに追加
    - execution/
      - __init__.py            # 注文実行ロジックをここに追加
    - monitoring/
      - __init__.py            # 監視・ロギングをここに追加

README やテスト、設定ファイル等はプロジェクトルートに配置してください（例: README.md, requirements.txt, setup.cfg など）。

ツリー表記（簡易）
```
project-root/
├─ src/
│  └─ kabusys/
│     ├─ __init__.py
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
└─ README.md
```

---

## 開発ガイドライン（簡易）

- 各機能は該当サブパッケージ内に実装する（例: strategy 内に複数の戦略ファイルを追加）
- 公開 API（ユーザが import する関数やクラス）はトップレベルの __init__.py で必要に応じてエクスポートする
- 実際の取引を行う場合は、テスト用のシミュレーション環境（ペーパー取引）で十分に検証すること
- 機密情報（APIキー等）は環境変数や安全なシークレット管理を利用し、ソース管理に含めないこと

---

## 今後の拡張案（例）

- 取引所・ブローカー固有の API クライアント実装
- シミュレーション（バックテスト）モジュールの追加
- リアルタイム監視ダッシュボードや通知機能の強化
- 戦略テンプレート／サンプルの追加

---

必要に応じてこの README をプロジェクトの実装に合わせて更新してください。質問や具体的な実装例が欲しい場合は、実装したい機能（例: どの証券会社APIを使うか、どんな戦略を作りたいか）を教えてください。